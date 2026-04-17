"""AI자문 데이터 수집 레이어.

15분봉(KR/US) + 기술적 지표(MACD/RSI/Stoch/BB/MA) + 사업별 매출비중.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

import requests

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL
from routers._kis_auth import get_access_token_safe
from stock.indicators import calc_technical_indicators


# ── KIS 1분봉 → 15분봉 리샘플 ────────────────────────────────────────────────

def _fetch_15min_ohlcv_kr_yf(code: str) -> list[dict]:
    """yfinance 기반 국내 15분봉 (최대 60일치). .KS/.KQ suffix 사용."""
    try:
        from stock.market import _kr_yf_ticker_str
        from stock.yf_client import _ticker

        ticker_str = _kr_yf_ticker_str(code)
        if not ticker_str:
            return []

        hist = _ticker(ticker_str).history(period="60d", interval="15m")
        if hist is None or hist.empty:
            return []

        result = []
        for ts, row in hist.iterrows():
            try:
                ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
            except Exception:
                continue
            c = float(row.get("Close", 0) or 0)
            if c == 0:
                continue
            result.append({
                "time": ts_str,
                "open": float(row.get("Open", c)),
                "high": float(row.get("High", c)),
                "low": float(row.get("Low", c)),
                "close": c,
                "volume": int(row.get("Volume", 0) or 0),
            })

        return result[-300:]
    except Exception:
        return []


def fetch_15min_ohlcv_kr(code: str) -> list[dict]:
    """KIS REST API FHKST03010200 (1분봉) 수집 후 15분봉으로 리샘플.

    하루치가 부족(< 30봉)하면 yfinance .KS/.KQ fallback으로 5일치 수집.
    KIS 키 미설정 시 즉시 yfinance fallback.
    반환: [{time, open, high, low, close, volume}] 최근 300봉.
    """
    token = get_access_token_safe()
    if not token:
        return _fetch_15min_ohlcv_kr_yf(code)

    try:

        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": KIS_APP_KEY,
            "appsecret": KIS_APP_SECRET,
            "tr_id": "FHKST03010200",
            "custtype": "P",
        }

        # 여러 시간대 병렬 호출로 하루 전체 데이터 수집 (각 30봉씩, 총 120봉 ≈ 2시간치 1분봉)
        def _fetch_single_hour(hour_str: str) -> list[dict]:
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": code,
                "fid_input_hour_1": hour_str,
                "fid_pw_data_incu_yn": "Y",
                "fid_etc_cls_code": "",
            }
            bars = []
            try:
                resp = requests.get(
                    f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                    headers=headers,
                    params=params,
                    timeout=20,
                )
                if resp.status_code != 200:
                    return bars
                output2 = resp.json().get("output2") or []
                for item in output2:
                    t_str = item.get("stck_cntg_hour", "")
                    date_str = item.get("stck_bsop_date", "")
                    if not t_str or not date_str:
                        continue
                    dt_str = (
                        f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                        f"T{t_str[:2]}:{t_str[2:4]}:{t_str[4:6]}"
                    )
                    c = float(item.get("stck_prpr") or 0)
                    if c == 0:
                        continue
                    bars.append({
                        "time": dt_str,
                        "open": float(item.get("stck_oprc") or c),
                        "high": float(item.get("stck_hgpr") or c),
                        "low": float(item.get("stck_lwpr") or c),
                        "close": c,
                        "volume": int(item.get("cntg_vol") or 0),
                    })
            except Exception:
                pass
            return bars

        from concurrent.futures import ThreadPoolExecutor
        raw_bars_all: list[dict] = []
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_fetch_single_hour, h) for h in ["153000", "143000", "133000", "123000"]]
            for fut in futures:
                raw_bars_all.extend(fut.result())

        # 중복 제거 + 시간순 정렬
        seen: set[str] = set()
        raw_bars: list[dict] = []
        for bar in raw_bars_all:
            if bar["time"] not in seen:
                seen.add(bar["time"])
                raw_bars.append(bar)
        raw_bars.sort(key=lambda x: x["time"])

        # 15분 리샘플 (pandas)
        result: list[dict] = []
        if raw_bars:
            import pandas as pd
            df = pd.DataFrame(raw_bars)
            df["time"] = pd.to_datetime(df["time"])
            df = df.set_index("time")
            df15 = df.resample("15min").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna(subset=["close"])

            for ts, row in df15.iterrows():
                result.append({
                    "time": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]),
                })

        # KIS 데이터 30봉 미만이면 yfinance로 5일치 수집 (기술지표 계산에 충분한 데이터 확보)
        if len(result) < 30:
            yf_result = _fetch_15min_ohlcv_kr_yf(code)
            if yf_result:
                return yf_result

        return result[-300:]

    except Exception:
        return _fetch_15min_ohlcv_kr_yf(code)


def fetch_15min_ohlcv_us(code: str) -> list[dict]:
    """yfinance 15분봉 (최대 60일치). 최근 300봉 반환."""
    try:
        from stock.yf_client import _ticker
        t = _ticker(code.upper())
        hist = t.history(period="60d", interval="15m")
        if hist is None or hist.empty:
            return []

        result = []
        for ts, row in hist.iterrows():
            # Timezone-aware timestamp → naive ISO string
            try:
                ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
            except Exception:
                continue
            c = float(row.get("Close", 0) or 0)
            if c == 0:
                continue
            result.append({
                "time": ts_str,
                "open": float(row.get("Open", c)),
                "high": float(row.get("High", c)),
                "low": float(row.get("Low", c)),
                "close": c,
                "volume": int(row.get("Volume", 0) or 0),
            })

        return result[-300:]
    except Exception:
        return []


# ── 기술적 지표 계산: stock/indicators.py 분리 ─────────────────────────────────
# calc_technical_indicators는 stock.indicators에서 import (상단 참조)

# ── 타임프레임별 OHLCV 수집 ──────────────────────────────────────────────────

def _yf_hist_to_ohlcv_list(hist, max_bars: int = 3000) -> list[dict]:
    """yfinance history DataFrame → OHLCV list (최근 max_bars봉)."""
    if hist is None or hist.empty:
        return []
    result = []
    for ts, row in hist.iterrows():
        try:
            ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            continue
        c = float(row.get("Close", 0) or 0)
        if c == 0:
            continue
        result.append({
            "time": ts_str,
            "open": float(row.get("Open", c)),
            "high": float(row.get("High", c)),
            "low": float(row.get("Low", c)),
            "close": c,
            "volume": int(row.get("Volume", 0) or 0),
        })
    return result[-max_bars:]


def _fetch_ohlcv_kr_yf(code: str, interval: str = "15m", period: str = "60d") -> list[dict]:
    """yfinance 기반 국내 OHLCV (interval/period 지정). .KS/.KQ suffix 사용."""
    try:
        from stock.market import _kr_yf_ticker_str
        from stock.yf_client import _ticker

        ticker_str = _kr_yf_ticker_str(code)
        if not ticker_str:
            return []

        hist = _ticker(ticker_str).history(period=period, interval=interval)
        return _yf_hist_to_ohlcv_list(hist)
    except Exception as e:
        logger.warning("OHLCV KR 조회 실패 (%s, %s, %s): %s", code, interval, period, e)
        return []


def _fetch_ohlcv_us_yf(code: str, interval: str = "15m", period: str = "60d") -> list[dict]:
    """yfinance 기반 해외 OHLCV (interval/period 지정)."""
    try:
        from stock.yf_client import _ticker
        hist = _ticker(code.upper()).history(period=period, interval=interval)
        return _yf_hist_to_ohlcv_list(hist)
    except Exception as e:
        logger.warning("OHLCV US 조회 실패 (%s, %s, %s): %s", code, interval, period, e)
        return []


# yfinance interval별 최대 period 매핑
_YF_INTERVAL_MAP = {
    "15m":  "15m",
    "60m":  "60m",
    "1d":   "1d",
    "1wk":  "1wk",
}

_MAX_PERIOD = {
    "15m":  "60d",
    "60m":  "2y",
    "1d":   "10y",
    "1wk":  "10y",
}


def fetch_ohlcv_by_interval(code: str, market: str, interval: str = "15m", period: str = "60d") -> dict:
    """interval/period 지정 OHLCV 수집 + 기술지표 계산.

    interval: '15m' | '60m' | '1d' | '1wk'
    period: yfinance period string ('5d', '1mo', '60d', '6mo', '1y', '3y', '5y', '10y' 등)
    반환: {"ohlcv": [...], "indicators": {...}}
    """
    if interval not in _YF_INTERVAL_MAP:
        interval = "15m"

    yf_interval = _YF_INTERVAL_MAP[interval]

    if market == "KR":
        ohlcv = _fetch_ohlcv_kr_yf(code, interval=yf_interval, period=period)
    else:
        ohlcv = _fetch_ohlcv_us_yf(code, interval=yf_interval, period=period)

    indicators = calc_technical_indicators(ohlcv)
    return {"ohlcv": ohlcv, "indicators": indicators}


# ── 사업별 매출비중 + 사업 설명 + 테마 키워드 (KR — OpenAI 추론) ──────────────

def fetch_segments_kr(code: str, name: str) -> dict:
    """KR: OpenAI GPT에게 사업부문 매출비중 + 사업 설명 + 투자 테마 키워드 추론 요청.

    OPENAI_API_KEY 미설정 시 빈 dict 반환.
    반환: {"segments": [{segment, revenue_pct, note}], "description": str, "keywords": [str]}
    """
    empty = {"segments": [], "description": "", "keywords": []}
    if not OPENAI_API_KEY:
        return empty

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = (
            f"{name}(종목코드: {code})에 대해 다음 3가지를 JSON으로 알려주세요.\n"
            f"1. segments: 주요 사업부문 상위 4개 (각 항목 {{segment: 사업명, revenue_pct: 숫자}}). 비중 합계 100.\n"
            f"2. description: 이 기업이 무엇을 하는 회사인지 한국어로 2~3문장 서술.\n"
            f"3. keywords: 관련 투자 테마·키워드 5~8개 배열 (예: 반도체, AI, 2차전지 등).\n"
            f"불확실해도 최선의 추정값을 주세요."
        )

        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=600,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)

        # segments 파싱
        segs = data if isinstance(data, list) else data.get("segments", data.get("items", []))
        if isinstance(segs, list):
            pass
        else:
            segs = []
        result = []
        for s in segs[:4]:
            seg_name = s.get("segment") or s.get("name") or ""
            pct = s.get("revenue_pct") or s.get("pct") or s.get("percentage") or 0
            if seg_name:
                result.append({
                    "segment": seg_name,
                    "revenue_pct": float(pct),
                    "note": "AI추정",
                })

        description = data.get("description", "") if isinstance(data, dict) else ""
        keywords = data.get("keywords", []) if isinstance(data, dict) else []
        if not isinstance(keywords, list):
            keywords = []

        return {"segments": result, "description": description, "keywords": keywords[:8]}
    except Exception:
        return empty


# ── PER/PBR 5년 통계 (Phase 2-2) ─────────────────────────────────────────────

def fetch_valuation_stats(code: str, market: str) -> dict:
    """PER/PBR 5년 통계 (평균/최대/최소/현재/편차%).

    내부에서 `fetch_valuation_history_yf(code, years=5)` 호출 후 집계.
    반환:
      {
        "per_avg_5y", "per_max_5y", "per_min_5y", "per_current", "per_deviation_pct",
        "pbr_avg_5y", "pbr_max_5y", "pbr_min_5y", "pbr_current", "pbr_deviation_pct",
        "data_points": int,  # 집계에 사용된 월봉 수
      }
    데이터 부족 시 각 필드 None. 캐시 24시간.
    """
    from stock.cache import get_cached, set_cached
    from stock.yf_client import fetch_valuation_history_yf

    cache_key = f"valuation_stats:{market}:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    empty = {
        "per_avg_5y": None, "per_max_5y": None, "per_min_5y": None,
        "per_current": None, "per_deviation_pct": None,
        "pbr_avg_5y": None, "pbr_max_5y": None, "pbr_min_5y": None,
        "pbr_current": None, "pbr_deviation_pct": None,
        "data_points": 0,
    }

    try:
        # yfinance는 국내 종목에 대해 .KS/.KQ suffix 처리가 필요 — fetch_valuation_history_yf는 code를 그대로 사용
        # 국내는 stock.market.fetch_valuation_history()가 빈 배열 반환하므로 (pykrx 스크래핑 불가)
        # yfinance ticker string으로 변환해서 직접 호출
        if market == "KR":
            from stock.market import _kr_yf_ticker_str
            ticker_str = _kr_yf_ticker_str(code)
            if not ticker_str:
                set_cached(cache_key, empty, ttl_hours=24)
                return empty
            history = fetch_valuation_history_yf(ticker_str, years=5)
        else:
            history = fetch_valuation_history_yf(code, years=5)

        if not history or not isinstance(history, list):
            set_cached(cache_key, empty, ttl_hours=24)
            return empty

        per_vals = [h["per"] for h in history if h.get("per") is not None and h["per"] > 0]
        pbr_vals = [h["pbr"] for h in history if h.get("pbr") is not None and h["pbr"] > 0]

        result = dict(empty)
        result["data_points"] = len(history)

        if per_vals:
            per_avg = sum(per_vals) / len(per_vals)
            per_cur = per_vals[-1]
            result["per_avg_5y"] = round(per_avg, 2)
            result["per_max_5y"] = round(max(per_vals), 2)
            result["per_min_5y"] = round(min(per_vals), 2)
            result["per_current"] = round(per_cur, 2)
            if per_avg > 0:
                result["per_deviation_pct"] = round((per_cur - per_avg) / per_avg * 100, 1)

        if pbr_vals:
            pbr_avg = sum(pbr_vals) / len(pbr_vals)
            pbr_cur = pbr_vals[-1]
            result["pbr_avg_5y"] = round(pbr_avg, 2)
            result["pbr_max_5y"] = round(max(pbr_vals), 2)
            result["pbr_min_5y"] = round(min(pbr_vals), 2)
            result["pbr_current"] = round(pbr_cur, 2)
            if pbr_avg > 0:
                result["pbr_deviation_pct"] = round((pbr_cur - pbr_avg) / pbr_avg * 100, 1)

        set_cached(cache_key, result, ttl_hours=24)
        return result
    except Exception as e:
        logger.debug("fetch_valuation_stats 실패 [%s %s]: %s", code, market, e)
        set_cached(cache_key, empty, ttl_hours=24)
        return empty

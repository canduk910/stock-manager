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

        # 여러 시간대 호출로 하루 전체 데이터 수집 (각 30봉씩, 총 120봉 ≈ 2시간치 1분봉)
        raw_bars_all: list[dict] = []
        for hour_str in ["153000", "143000", "133000", "123000"]:
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": code,
                "fid_input_hour_1": hour_str,
                "fid_pw_data_incu_yn": "Y",
                "fid_etc_cls_code": "",
            }
            try:
                resp = requests.get(
                    f"{KIS_BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
                    headers=headers,
                    params=params,
                    timeout=20,
                )
                if resp.status_code != 200:
                    continue
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
                    raw_bars_all.append({
                        "time": dt_str,
                        "open": float(item.get("stck_oprc") or c),
                        "high": float(item.get("stck_hgpr") or c),
                        "low": float(item.get("stck_lwpr") or c),
                        "close": c,
                        "volume": int(item.get("cntg_vol") or 0),
                    })
            except Exception:
                continue

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

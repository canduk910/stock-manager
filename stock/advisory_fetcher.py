"""AI자문 데이터 수집 레이어.

15분봉(KR/US) + 기술적 지표(MACD/RSI/Stoch/BB/MA) + 사업별 매출비중.

데이터 수집 경로:
  1. KIS REST API (FHKST03010200) — 국내 1분봉 → 15분 resample
     - 시간대별 4회 병렬 호출 (ThreadPoolExecutor, 15:30/14:30/13:30/12:30)
     - 30봉 미만이면 yfinance .KS/.KQ suffix fallback
  2. yfinance — 해외 15분봉 + interval별 OHLCV (15m/60m/1d/1wk)
  3. OpenAI GPT — 국내 사업부문 매출비중 + 설명 + 키워드 추론 (1회 호출)
  4. yfinance 분기 재무 — PER/PBR 5년 통계 (avg/max/min/deviation)

기술지표 계산은 stock.indicators.calc_technical_indicators()에 위임한다.
KIS 토큰은 routers/_kis_auth.get_access_token_safe()를 사용한다
(과거 모듈 내 자체 캐시 → _kis_auth 공통 모듈로 이관됨).
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

import requests

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL
from routers._kis_auth import get_access_token_safe
from stock.indicators import calc_technical_indicators
from stock.kis_overseas_client import get_kis_ohlcv_15min


# ── KIS 1분봉 → 15분봉 리샘플 ────────────────────────────────────────────────

def _fetch_15min_ohlcv_kr_yf(code: str) -> list[dict]:
    """yfinance 기반 국내 15분봉 fallback (최대 60일치). .KS/.KQ suffix 사용.

    KIS API 키 미설정이거나 KIS 데이터가 30봉 미만일 때 사용.
    yfinance 15m interval은 최대 60일까지만 조회 가능 (Yahoo 제한).
    반환: [{time, open, high, low, close, volume}] 최근 300봉.
    """
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

    수집 전략:
      1. KIS 1분봉을 시간대별 4회 병렬 호출 (153000/143000/133000/123000)
         - 각 시간대에서 약 30봉(30분치) 반환 → 총 ~120봉(2시간) 수집
         - ThreadPoolExecutor(max_workers=4)로 병렬화하여 지연 최소화
      2. 중복 제거(time 기준) + 시간순 정렬 후 pandas resample('15min')
      3. 15분봉이 30봉 미만이면 yfinance fallback으로 60일치 수집

    하루치가 부족(< 30봉)하면 yfinance .KS/.KQ fallback으로 수집.
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
        # fid_input_hour_1: 기준 시각. "153000"(15:30 장 마감)부터 역순 조회해야
        # 전 거래일 데이터가 정상 반환됨 (장중 시각 지정 시 빈 응답 위험)
        # fid_etc_cls_code: 빈 문자열 필수. 누락 시 "ERROR INPUT FIELD NOT FOUND" 오류 발생
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

        # KIS 데이터 30봉 미만이면 yfinance fallback (기술지표 계산에 최소 30봉 필요:
        # RSI 14봉 + MACD 26봉 초기값 등)
        if len(result) < 30:
            yf_result = _fetch_15min_ohlcv_kr_yf(code)
            if yf_result:
                return yf_result

        return result[-300:]

    except Exception:
        return _fetch_15min_ohlcv_kr_yf(code)


# 모듈 스코프에 _ticker 노출 (테스트/REQ-INTEG-08 KIS fallback 경로 공용)
from stock.yf_client import _ticker  # noqa: E402


def _normalize_kis_15min_to_advisory(rows: list[dict]) -> list[dict]:
    """KIS 15분봉 응답 → advisory_fetcher 표준 OHLCV 형식.

    표준 키: time/open/high/low/close/volume.
    KIS 응답에는 datetime/time 둘 다 있으므로 time을 보존하면서 open/high/low/close 형식 통일.
    """
    out = []
    for r in rows:
        try:
            ts_str = r.get("time") or r.get("datetime")
            close = float(r.get("close") or 0)
            if not ts_str or close <= 0:
                continue
            out.append({
                "time": ts_str,
                "open": float(r.get("open") or close),
                "high": float(r.get("high") or close),
                "low": float(r.get("low") or close),
                "close": close,
                "volume": int(float(r.get("volume") or 0)),
            })
        except (TypeError, ValueError):
            continue
    return out


def fetch_15min_ohlcv_us(code: str) -> list[dict]:
    """미국 15분봉 (60일치). 최근 300봉 반환.

    REQ-INTEG-08: KIS 우선(HHDFS76950200) → 실패 시 yfinance fallback (15분 지연).
    기술분석(MACD/RSI/Stochastic) 입력 호환: 정렬 과거→최신, 키 time/open/high/low/close/volume.
    """
    # ── KIS 우선 ───────────────────────────────────────────────────────────
    try:
        kis_rows = get_kis_ohlcv_15min(code, days=60)
    except Exception:
        kis_rows = None

    if kis_rows:
        normalized = _normalize_kis_15min_to_advisory(kis_rows)
        if normalized:
            return normalized[-300:]

    # ── yfinance fallback (기존 경로) ─────────────────────────────────────
    try:
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


# ── 기술적 지표 계산: stock/indicators.py에 위임 ──────────────────────────────
# calc_technical_indicators는 stock.indicators에서 import (상단 참조).
# 과거에는 이 파일에 인라인으로 존재했으나, 재사용성을 위해 indicators.py로 분리됨.
# advisory_service, pipeline_service 등 여러 서비스에서 indicators.py를 직접 사용.

# ── 타임프레임별 OHLCV 수집 ──────────────────────────────────────────────────

def _yf_hist_to_ohlcv_list(hist, max_bars: int = 3000) -> list[dict]:
    """yfinance history DataFrame → OHLCV dict list 변환 (최근 max_bars봉).

    max_bars=3000: 10년 일봉(약 2,447행)을 커버하기 위한 값.
    초기값 500에서 확장됨 — 장기 밸류에이션 차트에서 데이터 절삭 방지.
    Close=0인 행은 비정상 데이터로 간주하여 건너뜀.
    """
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
    """yfinance 기반 국내 OHLCV (interval/period 지정). .KS/.KQ suffix 사용.

    국내 종목은 6자리 숫자 코드를 stock.market._kr_yf_ticker_str()로
    .KS(KOSPI) 또는 .KQ(KOSDAQ) suffix 붙은 yfinance 티커로 변환해야 한다.
    """
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


# yfinance interval별 허용 interval 매핑 (입력값 → yfinance 파라미터)
_YF_INTERVAL_MAP = {
    "15m":  "15m",
    "60m":  "60m",
    "1d":   "1d",
    "1wk":  "1wk",
}

# yfinance interval별 최대 조회 기간 제한 (Yahoo Finance 서버 제약)
# 이 제한을 초과하면 yfinance가 빈 DataFrame을 반환하거나 에러 발생
_MAX_PERIOD = {
    "15m":  "60d",    # 15분봉: 최대 60일 (약 2개월)
    "60m":  "2y",     # 60분봉: 최대 2년
    "1d":   "10y",    # 일봉: 최대 10년
    "1wk":  "10y",    # 주봉: 최대 10년
}


def fetch_ohlcv_by_interval(code: str, market: str, interval: str = "15m", period: str = "60d") -> dict:
    """interval/period 지정 OHLCV 수집 + 기술지표 자동 계산.

    Args:
        code: 종목코드 (국내 6자리 / 해외 티커)
        market: 'KR' | 'US'
        interval: '15m' | '60m' | '1d' | '1wk' (미지원 값은 '15m' fallback)
        period: yfinance period 문자열 ('5d', '1mo', '60d', '6mo', '1y', '3y', '5y', '10y' 등)

    Returns:
        {"ohlcv": [{time, open, high, low, close, volume}, ...],
         "indicators": {macd, rsi, stoch, bb, ma, current_signals, ...}}

    OHLCV 수집 후 stock.indicators.calc_technical_indicators()를 자동 호출하여
    기술지표를 함께 반환한다. 프론트엔드 TechnicalPanel에서 사용.
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

def fetch_segments_kr(code: str, name: str, user_id=None) -> dict:
    """KR: OpenAI GPT에게 사업부문 매출비중 + 사업 설명 + 투자 테마 키워드를 1회 호출로 통합 추론.

    GPT 1회 호출로 3가지(segments/description/keywords)를 JSON response_format으로 요청.
    과거에는 항목별 별도 호출이었으나 API 비용 절감 + 응답 일관성을 위해 통합.
    max_completion_tokens=600: 4개 사업부문 + 2~3문장 설명 + 8개 키워드에 충분한 토큰.

    Args:
        code: 종목코드 (6자리)
        name: 종목명 (GPT 프롬프트에 사용)
        user_id: AI 게이트웨이 쿼터 추적용 사용자 ID (None이면 시스템 호출)

    Returns:
        {"segments": [{segment, revenue_pct, note}], "description": str, "keywords": [str]}
        OPENAI_API_KEY 미설정 시 빈 구조 반환.
    """
    empty = {"segments": [], "description": "", "keywords": []}
    if not OPENAI_API_KEY:
        return empty

    try:
        from services.ai_gateway import call_openai_chat

        prompt = (
            f"{name}(종목코드: {code})에 대해 다음 3가지를 JSON으로 알려주세요.\n"
            f"1. segments: 주요 사업부문 상위 4개 (각 항목 {{segment: 사업명, revenue_pct: 숫자}}). 비중 합계 100.\n"
            f"2. description: 이 기업이 무엇을 하는 회사인지 한국어로 2~3문장 서술.\n"
            f"3. keywords: 관련 투자 테마·키워드 5~8개 배열 (예: 반도체, AI, 2차전지 등).\n"
            f"불확실해도 최선의 추정값을 주세요."
        )

        resp = call_openai_chat(
            messages=[{"role": "user", "content": prompt}],
            user_id=user_id,
            service_name="segments_kr",
            max_completion_tokens=600,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)

        # segments 파싱: GPT 응답이 루트 배열인 경우와 object인 경우 모두 대응
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


# ── 사업부문 매출비중 5년 추이 (KR — OpenAI 통합 추론, Phase 1A 2026-05-10) ──
# ValueScreener 자문(2026-05-10): GPT 통합 추론 + "AI 추정" 면책 의무 + composite_score 미반영.
# DART 사업보고서 본문 파싱(Phase B)은 차후. 5년치(Graham "지속성" 원칙 정합).

_SEGMENTS_HISTORY_HIGHLIGHT_THRESHOLD_PCT = 5.0  # 첫·끝 연도 ±5%p 임계


def _compute_segments_highlights(years_data: list) -> dict:
    """첫 연도 vs 끝 연도 비교로 신사업/축소사업 식별.

    ±5%p 임계 (ValueScreener 권고). Graham "사양 사업 위장 성장" Value Trap 식별용.
    """
    if not years_data or len(years_data) < 2:
        return {"growing": [], "shrinking": []}
    first = years_data[0].get("segments") or []
    last = years_data[-1].get("segments") or []
    first_pct = {s.get("segment"): float(s.get("revenue_pct") or 0) for s in first if s.get("segment")}
    last_pct = {s.get("segment"): float(s.get("revenue_pct") or 0) for s in last if s.get("segment")}
    all_segments = set(first_pct) | set(last_pct)
    growing, shrinking = [], []
    for seg in all_segments:
        delta = last_pct.get(seg, 0) - first_pct.get(seg, 0)
        if delta >= _SEGMENTS_HISTORY_HIGHLIGHT_THRESHOLD_PCT:
            growing.append({"segment": seg, "delta_pct": round(delta, 1)})
        elif delta <= -_SEGMENTS_HISTORY_HIGHLIGHT_THRESHOLD_PCT:
            shrinking.append({"segment": seg, "delta_pct": round(delta, 1)})
    growing.sort(key=lambda x: -x["delta_pct"])
    shrinking.sort(key=lambda x: x["delta_pct"])
    return {"growing": growing, "shrinking": shrinking}


def fetch_segments_history_kr(
    code: str, name: str, *, years: int = 5, user_id=None
) -> dict:
    """KR 사업부문 매출비중 N년치 추이.

    Phase B (2026-05-10): DART 사업보고서 본문 직접 파싱 1순위 + GPT fallback.
    - DART 파싱 성공 → source="dart_parsed", confidence="high" (실측)
    - DART 실패 (corp_code 미존재, 본문 다운/표 미발견 등) → GPT fallback
      (source="gpt_inference", confidence="low")
    - DART 부분 성공 (일부 연도만) → 부분 + GPT 보강 또는 DART 단독 (covered_years 메타)

    캐시 키: advisor:segments_history_kr:{code}:{years}, TTL 168h(7일).
    `service_name="segments_history_kr"` (GPT fallback 시).

    반환:
        {
            "years_data": [{"year": int, "segments": [{segment, revenue_pct, note}]}, ...],
            "highlights": {"growing": [{segment, delta_pct}], "shrinking": [...]},
            "confidence": "high" | "low",
            "source": "dart_parsed" | "gpt_inference" | "mixed",
            "covered_years": int,  # DART 파싱 성공 연도 수 (mixed/dart_parsed 시)
        }
    """
    from stock.cache import get_cached, set_cached
    from datetime import date

    empty = {"years_data": [], "highlights": {"growing": [], "shrinking": []},
             "confidence": "low", "source": "gpt_inference"}

    cache_key = f"advisor:segments_history_kr:{code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # Phase B: DART 본문 파싱 1순위 (실측)
    try:
        from stock.dart_segments import fetch_segments_history_dart
        dart_result = fetch_segments_history_dart(code, name, years=years, user_id=user_id)
        if dart_result.get("years_data"):
            # DART 성공 — 표시 전용 캐시 저장 후 반환
            set_cached(cache_key, dart_result, ttl_hours=24 * 7)
            return dart_result
    except Exception:
        # DART 파싱 실패는 silent — GPT fallback 진행
        pass

    if not OPENAI_API_KEY:
        return empty

    try:
        from services.ai_gateway import call_openai_chat

        latest_year = date.today().year - 1  # 사업보고서 공시 주기 반영
        start_year = latest_year - years + 1

        system_prompt = (
            "당신은 한국 가치투자 자문 시스템의 사업부문 추적 보조다. "
            "공시 자료(DART 사업보고서)에 한정한 추정만 제공하고, 불확실 시 추정값을 "
            "표시하되 'AI추정' 임을 명시한다. 연도 간 동일 사업은 일관된 명칭을 유지한다."
        )

        user_prompt = (
            f"{name}(종목코드: {code})의 최근 {years}년({start_year}~{latest_year}) "
            f"사업부문별 매출비중을 JSON으로 알려주세요.\n"
            f"형식: {{\"years_data\": [{{\"year\": {latest_year}, \"segments\": "
            f"[{{\"segment\": \"부문명\", \"revenue_pct\": 숫자}}]}}, ...]}}\n"
            f"규칙:\n"
            f"- 각 연도 segments 합계는 100\n"
            f"- 상위 4개 부문만\n"
            f"- 연도 간 동일 사업 부문 명칭 통일 (변화 추적 위해)\n"
            f"- 사업 신규 진출/철수도 0% 또는 등장으로 반영\n"
            f"- 불확실해도 최선의 추정값 (공시 한정)"
        )

        resp = call_openai_chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            user_id=user_id,
            service_name="segments_history_kr",
            max_completion_tokens=1500,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)

        raw_years = data.get("years_data") or data.get("years") or []
        if not isinstance(raw_years, list):
            return empty

        years_data = []
        for entry in raw_years:
            if not isinstance(entry, dict):
                continue
            year = entry.get("year")
            try:
                year = int(year)
            except (TypeError, ValueError):
                continue
            raw_segs = entry.get("segments") or []
            if not isinstance(raw_segs, list):
                continue
            segs = []
            for s in raw_segs[:4]:
                if not isinstance(s, dict):
                    continue
                seg_name = s.get("segment") or s.get("name") or ""
                pct = s.get("revenue_pct") or s.get("pct") or s.get("percentage") or 0
                if seg_name:
                    try:
                        segs.append({
                            "segment": str(seg_name),
                            "revenue_pct": float(pct),
                            "note": "AI추정",
                        })
                    except (TypeError, ValueError):
                        continue
            if segs:
                years_data.append({"year": year, "segments": segs})

        years_data.sort(key=lambda x: x["year"])
        if not years_data:
            return empty

        result = {
            "years_data": years_data,
            "highlights": _compute_segments_highlights(years_data),
            "confidence": "low",
            "source": "gpt_inference",
        }
        set_cached(cache_key, result, ttl_hours=24 * 7)
        return result
    except Exception:
        return empty


# ── 비즈니스 모델 narrative (KR/US 공통, 도메인 자문 적용) ────────────────────

_BUSINESS_MODEL_SYSTEM_PROMPT = (
    "당신은 한국 가치투자 자문 시스템의 분석 보조다. "
    "주어진 사업 부문/사업 설명/현금흐름 수치만 사용하여 회사의 비즈니스 모델을 한국어로 설명한다. "
    "추측이 어려운 부분은 단정하지 말고 '공시 정보 한정' 같은 한계를 명시한다.\n"
    "\n"
    "[현금 창출 narrative — MarginAnalyst 가이드]\n"
    "- 영업현금흐름과 순이익 비교를 언급(가능 시 OCF/NI 비율). 1.0 이상이면 현금 전환력 양호.\n"
    "- FCF 마진(FCF/매출)과 3년 부호 일관성 함께 기술. 양수 지속+5% 이상이면 안전마진 우호.\n"
    "- Capex 강도(capex/OCF) 분류: <30% 자산경량, 30~70% 정상, >70% 자본집약·FCF 압박.\n"
    "- 잉여현금 사용처(배당/자사주/M&A/부채상환)를 financing_cf 부호로 추정하고 환원율 지속가능성 평가.\n"
    "- 운전자본·일회성 항목으로 OCF가 부풀려졌을 가능성 의심 시 '현금흐름 품질 주의' 한 줄 명시.\n"
    "\n"
    "[R&D 전략 narrative — ValueScreener 가이드]\n"
    "- R&D 투자 성격을 기존 moat 강화(방어형) vs 신사업 발굴(공격형)로 구분. keywords·segments에서 단서 추출.\n"
    "- 산업 평균 R&D 비중 (반도체 8~15%, 제약 15~20%, 소비재 1~3%) 대비 과소·과대 여부 언급.\n"
    "- R&D 누적이 매출 성장·신제품으로 전환되는지(자본배분 효율) 또는 비용만 늘고 정체인지 판단.\n"
    "- Value trap 경계: R&D 증액에도 매출 CAGR 0% 이하거나, R&D 축소+배당 확대로 미래 성장 포기 시 명시.\n"
    "- 공시 정보로 확인 불가한 항목은 추측 금지, '공시 한정으로 단정 어려움'으로 한계 표기.\n"
    "\n"
    "응답은 반드시 JSON 형식으로 다음 키를 포함한다:\n"
    "  revenue_model: 어떤 고객(B2B/B2C/B2G)에게 어떤 채널로 무엇을 팔아 매출을 만드는지 3~4문장.\n"
    "  cash_generation: 위 가이드에 따른 현금 창출 분석 3~4문장.\n"
    "  rd_strategy: 위 가이드에 따른 R&D 전략 분석 2~3문장.\n"
    "각 값은 한국어 평문 문자열이며 마크다운/불릿 금지."
)

_BUSINESS_MODEL_CACHE_TTL_HOURS = 7 * 24  # 7일


def _empty_business_model() -> dict:
    return {"revenue_model": None, "cash_generation": None, "rd_strategy": None}


def _format_cf_context(financial: dict | None) -> str:
    """현금흐름 + 매출/이익 최근 3년 요약을 GPT 프롬프트용 한 줄 문자열로 변환."""
    if not financial:
        return "(재무 데이터 없음)"
    cf = financial.get("cashflow") or []
    is_ = financial.get("income_stmt") or financial.get("income") or []

    def _last3(rows: list, key: str) -> list:
        out = []
        for row in rows[-3:]:
            v = row.get(key) if isinstance(row, dict) else None
            out.append(v)
        return out

    parts = []
    parts.append(f"매출(최근3): {_last3(is_, 'revenue')}")
    parts.append(f"순이익(최근3): {_last3(is_, 'net_income')}")
    parts.append(f"영업CF(최근3): {_last3(cf, 'operating_cf')}")
    parts.append(f"투자CF(최근3): {_last3(cf, 'investing_cf')}")
    parts.append(f"재무CF(최근3): {_last3(cf, 'financing_cf')}")
    parts.append(f"CAPEX(최근3): {_last3(cf, 'capex')}")
    parts.append(f"FCF(최근3): {_last3(cf, 'free_cf')}")
    return "; ".join(parts)


def fetch_business_model(
    code: str,
    name: str,
    market: str,
    segments_dict: dict | None,
    financial_dict: dict | None,
    user_id=None,
) -> dict:
    """비즈니스 모델 narrative — revenue_model / cash_generation / rd_strategy.

    GPT 1회 호출(JSON object). MarginAnalyst + ValueScreener 도메인 가이드를 시스템
    프롬프트에 내장. 매 호출마다 GPT를 부르지 않도록 cache TTL 7일.

    Args:
        code: 종목코드
        name: 종목명
        market: 'KR' | 'US'
        segments_dict: fetch_segments_kr/us 결과 ({segments, description, keywords})
        financial_dict: 손익계산서/현금흐름표 dict
        user_id: AI 게이트웨이 쿼터 추적용 (None이면 시스템 호출)

    Returns:
        {"revenue_model": str|None, "cash_generation": str|None, "rd_strategy": str|None}
    """
    from stock.cache import get_cached, set_cached

    cache_key = f"advisor:business_model:{market}:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    if not OPENAI_API_KEY:
        return _empty_business_model()

    segments = (segments_dict or {}).get("segments") or []
    description = (segments_dict or {}).get("description") or ""
    keywords = (segments_dict or {}).get("keywords") or []

    user_prompt = (
        f"종목명: {name} (코드 {code}, 시장 {market})\n"
        f"사업 설명: {description or '(없음)'}\n"
        f"투자 키워드: {', '.join(keywords) if keywords else '(없음)'}\n"
        f"사업부문 매출비중: {segments or '(없음)'}\n"
        f"재무 컨텍스트: {_format_cf_context(financial_dict)}\n"
        f"\n위 정보를 토대로 revenue_model / cash_generation / rd_strategy 3개 키를 가진 JSON을 생성하라."
    )

    try:
        from services.ai_gateway import call_openai_chat

        resp = call_openai_chat(
            messages=[
                {"role": "system", "content": _BUSINESS_MODEL_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            user_id=user_id,
            service_name="advisory_business_model",
            max_completion_tokens=1500,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content) if isinstance(content, str) else {}
        if not isinstance(data, dict):
            return _empty_business_model()

        result = {
            "revenue_model": (data.get("revenue_model") or "").strip() or None,
            "cash_generation": (data.get("cash_generation") or "").strip() or None,
            "rd_strategy": (data.get("rd_strategy") or "").strip() or None,
        }
        # 모든 필드가 None이면 캐시하지 않음 (다음에 재시도)
        if any(v for v in result.values()):
            set_cached(cache_key, result, ttl_hours=_BUSINESS_MODEL_CACHE_TTL_HOURS)
        return result
    except Exception:
        logger.exception("fetch_business_model failed for %s/%s", market, code)
        return _empty_business_model()


# ── PER/PBR 5년 통계 (Phase 2-2) ─────────────────────────────────────────────

def fetch_valuation_stats(code: str, market: str) -> dict:
    """PER/PBR 5년 통계 (평균/최대/최소/현재/편차%).

    내부에서 yf_client.fetch_valuation_history_yf(code, years=5)를 호출한 뒤
    월별 PER/PBR 시계열을 집계하여 통계를 산출한다.

    편차%: (현재값 - 5년 평균) / 5년 평균 × 100
      양수면 역사적 평균 대비 고평가, 음수면 저평가를 의미.

    Args:
        code: 종목코드 (국내 6자리 / 해외 티커)
        market: 'KR' | 'US'. KR인 경우 _kr_yf_ticker_str()로 .KS/.KQ 변환 필요.

    Returns:
        {per_avg_5y, per_max_5y, per_min_5y, per_current, per_deviation_pct,
         pbr_avg_5y, pbr_max_5y, pbr_min_5y, pbr_current, pbr_deviation_pct,
         data_points: int}
        데이터 부족 시 각 필드 None.

    캐시: 'valuation_stats:{market}:{code}' 키, TTL 24시간.
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
        # 국내 종목: stock.market.fetch_valuation_history()는 pykrx 스크래핑 불가로 빈 배열 반환.
        # 따라서 _kr_yf_ticker_str()로 .KS/.KQ suffix 변환 후
        # yfinance fetch_valuation_history_yf()를 직접 호출한다.
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

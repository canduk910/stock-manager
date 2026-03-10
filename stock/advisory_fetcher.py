"""AI자문 데이터 수집 레이어.

15분봉(KR/US) + 기술적 지표(MACD/RSI/Stoch/BB/MA) + 사업별 매출비중.
"""

from __future__ import annotations

import json
import math
import os
import time
from typing import Optional

import requests


# ── KIS 토큰 캐시 (모듈 수준, 분당 1회 제한 대응) ────────────────────────────
_kis_token_cache: dict = {"token": None, "expires_at": 0.0}


def _get_kis_token() -> str | None:
    """KIS access_token 반환. 유효한 토큰이 캐시에 있으면 재사용, 없으면 새로 발급."""
    now = time.time()
    if _kis_token_cache["token"] and now < _kis_token_cache["expires_at"]:
        return _kis_token_cache["token"]

    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = os.getenv("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"

    if not app_key or not app_secret:
        return None

    try:
        resp = requests.post(
            f"{base_url}/oauth2/tokenP",
            headers={"content-type": "application/json"},
            data=json.dumps({
                "grant_type": "client_credentials",
                "appkey": app_key,
                "appsecret": app_secret,
            }),
            timeout=10,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        token = data.get("access_token")
        if not token:
            return None
        # 만료 여유시간 60초 확보
        expires_in = int(data.get("expires_in", 86400))
        _kis_token_cache["token"] = token
        _kis_token_cache["expires_at"] = now + expires_in - 60
        return token
    except Exception:
        return None


# ── KIS 1분봉 → 15분봉 리샘플 ────────────────────────────────────────────────

def _fetch_15min_ohlcv_kr_yf(code: str) -> list[dict]:
    """yfinance 기반 국내 15분봉 (최대 60일치). .KS/.KQ suffix 사용."""
    try:
        from stock.market import _kr_yf_ticker_str
        import yfinance as yf

        ticker_str = _kr_yf_ticker_str(code)
        if not ticker_str:
            return []

        hist = yf.Ticker(ticker_str).history(period="60d", interval="15m")
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
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = os.getenv("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"

    if not app_key or not app_secret:
        return _fetch_15min_ohlcv_kr_yf(code)

    try:
        token = _get_kis_token()
        if not token:
            return _fetch_15min_ohlcv_kr_yf(code)

        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": app_key,
            "appsecret": app_secret,
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
                    f"{base_url}/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
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
        import yfinance as yf
        t = yf.Ticker(code.upper())
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


# ── 기술적 지표 계산 ──────────────────────────────────────────────────────────

def _ema(values: list[float], period: int) -> list[Optional[float]]:
    """지수이동평균 (EMA). 초기 period개는 SMA로 시드."""
    result: list[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return result
    k = 2 / (period + 1)
    sma = sum(values[:period]) / period
    result[period - 1] = sma
    for i in range(period, len(values)):
        result[i] = values[i] * k + (result[i - 1] or 0) * (1 - k)
    return result


def _sma(values: list[float], period: int) -> list[Optional[float]]:
    result: list[Optional[float]] = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1:i + 1]) / period
    return result


def _rsi(closes: list[float], period: int = 14) -> list[Optional[float]]:
    """Wilder's RSI."""
    result: list[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        result[i] = 100 - (100 / (1 + rs))

    return result


def _stoch(highs: list[float], lows: list[float], closes: list[float], k_period: int = 14, d_period: int = 3):
    """Stochastic Oscillator %K, %D."""
    n = len(closes)
    k_vals: list[Optional[float]] = [None] * n
    for i in range(k_period - 1, n):
        h = max(highs[i - k_period + 1:i + 1])
        lo = min(lows[i - k_period + 1:i + 1])
        if h == lo:
            k_vals[i] = 50.0
        else:
            k_vals[i] = (closes[i] - lo) / (h - lo) * 100

    # %D = SMA(3) of %K (valid values only)
    d_vals: list[Optional[float]] = [None] * n
    valid_k = [(i, v) for i, v in enumerate(k_vals) if v is not None]
    for j in range(d_period - 1, len(valid_k)):
        chunk = [valid_k[j - d_period + 1 + x][1] for x in range(d_period)]
        idx = valid_k[j][0]
        d_vals[idx] = sum(chunk) / d_period

    return k_vals, d_vals


def _bollinger(closes: list[float], period: int = 20, sigma: float = 2.0):
    """볼린저밴드 (SMA ± sigma*std)."""
    n = len(closes)
    upper: list[Optional[float]] = [None] * n
    mid: list[Optional[float]] = [None] * n
    lower: list[Optional[float]] = [None] * n
    for i in range(period - 1, n):
        window = closes[i - period + 1:i + 1]
        avg = sum(window) / period
        std = math.sqrt(sum((x - avg) ** 2 for x in window) / period)
        mid[i] = avg
        upper[i] = avg + sigma * std
        lower[i] = avg - sigma * std
    return upper, mid, lower


def _safe_val(v: Optional[float]) -> Optional[float]:
    if v is None:
        return None
    return round(v, 4) if not math.isnan(v) and not math.isinf(v) else None


def calc_technical_indicators(ohlcv: list[dict]) -> dict:
    """pandas 없이 순수 Python으로 기술지표 계산.

    입력: [{time, open, high, low, close, volume}]
    반환: {macd, rsi, stoch, bb, ma, volatility_target, current_signals}
    """
    if len(ohlcv) < 2:
        return {
            "macd": {}, "rsi": {}, "stoch": {}, "bb": {}, "ma": {},
            "volatility_target": None,
            "current_signals": {
                "macd_cross": "none", "rsi_signal": "neutral",
                "stoch_signal": "neutral", "above_ma20": False,
            },
        }

    times = [b["time"] for b in ohlcv]
    opens = [b["open"] for b in ohlcv]
    highs = [b["high"] for b in ohlcv]
    lows = [b["low"] for b in ohlcv]
    closes = [b["close"] for b in ohlcv]

    # MACD
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [
        _safe_val((e12 - e26) if (e12 is not None and e26 is not None) else None)
        for e12, e26 in zip(ema12, ema26)
    ]
    macd_valid = [v if v is not None else 0.0 for v in macd_line]
    signal_line_raw = _ema(macd_valid, 9)
    signal_line = [_safe_val(v) for v in signal_line_raw]
    histogram = [
        _safe_val((m - s) if (m is not None and s is not None) else None)
        for m, s in zip(macd_line, signal_line)
    ]

    # RSI
    rsi_vals = [_safe_val(v) for v in _rsi(closes, 14)]

    # Stochastic
    k_raw, d_raw = _stoch(highs, lows, closes, 14, 3)
    k_vals = [_safe_val(v) for v in k_raw]
    d_vals = [_safe_val(v) for v in d_raw]

    # 볼린저밴드
    bb_upper_raw, bb_mid_raw, bb_lower_raw = _bollinger(closes, 20, 2.0)
    bb_upper = [_safe_val(v) for v in bb_upper_raw]
    bb_mid = [_safe_val(v) for v in bb_mid_raw]
    bb_lower = [_safe_val(v) for v in bb_lower_raw]

    # 이동평균
    ma5_raw = _sma(closes, 5)
    ma20_raw = _sma(closes, 20)
    ma60_raw = _sma(closes, 60)
    ma5 = [_safe_val(v) for v in ma5_raw]
    ma20 = [_safe_val(v) for v in ma20_raw]
    ma60 = [_safe_val(v) for v in ma60_raw]

    # 변동성 돌파 목표가 (K=0.5)
    volatility_target = None
    if len(ohlcv) >= 2:
        prev = ohlcv[-2]
        curr = ohlcv[-1]
        range_val = prev["high"] - prev["low"]
        volatility_target = _safe_val(curr["open"] + range_val * 0.5)

    # 현재 시그널 요약
    cur_close = closes[-1] if closes else 0

    # MACD 크로스 (마지막 2봉)
    macd_cross = "none"
    if len(macd_line) >= 2 and len(signal_line) >= 2:
        m_cur = macd_line[-1]
        m_prev = macd_line[-2]
        s_cur = signal_line[-1]
        s_prev = signal_line[-2]
        if all(v is not None for v in [m_cur, m_prev, s_cur, s_prev]):
            if m_prev < s_prev and m_cur >= s_cur:
                macd_cross = "golden"
            elif m_prev > s_prev and m_cur <= s_cur:
                macd_cross = "dead"

    # RSI 시그널
    rsi_cur = next((v for v in reversed(rsi_vals) if v is not None), None)
    rsi_signal = "neutral"
    if rsi_cur is not None:
        if rsi_cur >= 70:
            rsi_signal = "overbought"
        elif rsi_cur <= 30:
            rsi_signal = "oversold"

    # Stochastic 시그널
    k_cur = next((v for v in reversed(k_vals) if v is not None), None)
    stoch_signal = "neutral"
    if k_cur is not None:
        if k_cur >= 80:
            stoch_signal = "overbought"
        elif k_cur <= 20:
            stoch_signal = "oversold"

    # MA20 상회 여부
    ma20_cur = next((v for v in reversed(ma20) if v is not None), None)
    above_ma20 = (cur_close > ma20_cur) if (ma20_cur is not None and cur_close) else False

    return {
        "macd": {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "times": times,
        },
        "rsi": {
            "values": rsi_vals,
            "times": times,
        },
        "stoch": {
            "k": k_vals,
            "d": d_vals,
            "times": times,
        },
        "bb": {
            "upper": bb_upper,
            "mid": bb_mid,
            "lower": bb_lower,
            "times": times,
        },
        "ma": {
            "ma5": ma5,
            "ma20": ma20,
            "ma60": ma60,
            "times": times,
        },
        "volatility_target": volatility_target,
        "current_signals": {
            "macd_cross": macd_cross,
            "rsi_signal": rsi_signal,
            "rsi_value": rsi_cur,
            "stoch_signal": stoch_signal,
            "stoch_k": k_cur,
            "above_ma20": above_ma20,
            "ma20": ma20_cur,
            "current_price": _safe_val(cur_close),
        },
    }


# ── 타임프레임별 OHLCV 수집 ──────────────────────────────────────────────────

def _yf_hist_to_ohlcv_list(hist, max_bars: int = 500) -> list[dict]:
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
        import yfinance as yf

        ticker_str = _kr_yf_ticker_str(code)
        if not ticker_str:
            return []

        hist = yf.Ticker(ticker_str).history(period=period, interval=interval)
        return _yf_hist_to_ohlcv_list(hist)
    except Exception:
        return []


def _fetch_ohlcv_us_yf(code: str, interval: str = "15m", period: str = "60d") -> list[dict]:
    """yfinance 기반 해외 OHLCV (interval/period 지정)."""
    try:
        import yfinance as yf
        hist = yf.Ticker(code.upper()).history(period=period, interval=interval)
        return _yf_hist_to_ohlcv_list(hist)
    except Exception:
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


# ── 사업별 매출비중 (KR — OpenAI 추론) ───────────────────────────────────────

def fetch_segments_kr(code: str, name: str) -> list[dict]:
    """KR: OpenAI GPT에게 사업부문 매출비중 추론 요청.

    OPENAI_API_KEY 미설정 시 빈 리스트 반환.
    반환: [{segment, revenue_pct, note}] (note: "AI추정")
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        prompt = (
            f"{name}(종목코드: {code})의 주요 사업부문과 대략적인 매출 비중을 "
            f"JSON 배열로 알려주세요. 상위 4개 부문만, 각 항목은 {{segment: 사업명, revenue_pct: 숫자}} 형식으로. "
            f"비중 합계가 100이 되도록 하고, 불확실하면 추정임을 알고 있어도 최선의 값을 주세요."
        )

        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=400,
            response_format={"type": "json_object"},
        )

        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        # 응답이 {"segments": [...]} 또는 [...]일 수 있음
        segs = data if isinstance(data, list) else data.get("segments", data.get("items", []))
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
        return result
    except Exception:
        return []

"""기술적 지표 순수 계산 모듈.

pandas 없이 순수 Python으로 구현.
MACD / RSI(Wilder) / Stochastic / Bollinger Band / MA / ATR / 변동성돌파 목표가.

순수 계산 함수 8개 (_ema, _sma, _rsi, _stoch, _bollinger, _atr, _safe_val,
calc_technical_indicators). 외부 의존성 없음 — math, typing만 사용.

advisory_fetcher.py의 fetch_ohlcv_by_interval()에서 OHLCV 수집 후 자동 호출된다.
프론트엔드 TechnicalPanel에서 시각화에 사용하는 모든 지표가 이 모듈에서 계산된다.
"""
from __future__ import annotations

import math
from typing import Optional


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


def _atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> list[Optional[float]]:
    """Average True Range (Wilder 평균법).
    True Range = max(high-low, |high-prev_close|, |low-prev_close|)
    """
    n = len(closes)
    result: list[Optional[float]] = [None] * n
    if n < period + 1:
        return result
    tr_list = []
    for i in range(1, n):
        tr_list.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))
    if len(tr_list) < period:
        return result
    atr_val = sum(tr_list[:period]) / period
    result[period] = atr_val
    for i in range(period + 1, n):
        atr_val = (atr_val * (period - 1) + tr_list[i - 1]) / period
        result[i] = atr_val
    return result


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
            "volatility_target_k03": None,
            "volatility_target_k05": None,
            "volatility_target_k07": None,
            "current_signals": {
                "macd_cross": "none", "rsi_signal": "neutral",
                "stoch_signal": "neutral", "above_ma20": False,
                "ma_alignment": "혼합", "atr": None,
                "volatility_target_k03": None,
                "volatility_target_k05": None,
                "volatility_target_k07": None,
            },
        }

    times = [b["time"] for b in ohlcv]
    opens = [b["open"] for b in ohlcv]
    highs = [b["high"] for b in ohlcv]
    lows = [b["low"] for b in ohlcv]
    closes = [b["close"] for b in ohlcv]
    volumes = [b.get("volume") or 0 for b in ohlcv]

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

    # ATR (14기간, Wilder)
    atr_raw = _atr(highs, lows, closes, 14)
    atr_cur = next((v for v in reversed(atr_raw) if v is not None), None)

    # 변동성 돌파 목표가 K=0.3/0.5/0.7
    volatility_target = None
    volatility_target_k03 = volatility_target_k05 = volatility_target_k07 = None
    if len(ohlcv) >= 2:
        range_val = ohlcv[-2]["high"] - ohlcv[-2]["low"]
        open_cur  = ohlcv[-1]["open"]
        volatility_target_k03 = _safe_val(open_cur + range_val * 0.3)
        volatility_target_k05 = _safe_val(open_cur + range_val * 0.5)
        volatility_target_k07 = _safe_val(open_cur + range_val * 0.7)
        volatility_target = volatility_target_k05

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

    # MA 현재값
    ma5_cur  = next((v for v in reversed(ma5)  if v is not None), None)
    ma20_cur = next((v for v in reversed(ma20) if v is not None), None)
    ma60_cur = next((v for v in reversed(ma60) if v is not None), None)

    # MA20 상회 여부
    above_ma20 = (cur_close > ma20_cur) if (ma20_cur is not None and cur_close) else False

    # MA 정배열/역배열
    ma_alignment = "혼합"
    if all(v is not None for v in [ma5_cur, ma20_cur, ma60_cur]):
        if ma5_cur > ma20_cur > ma60_cur:
            ma_alignment = "정배열"
        elif ma5_cur < ma20_cur < ma60_cur:
            ma_alignment = "역배열"

    # 거래량 신호 (Phase 2-1)
    volume_5d_avg: Optional[float] = None
    volume_20d_avg: Optional[float] = None
    volume_signal: Optional[float] = None
    cur_volume = volumes[-1] if volumes else 0
    if len(volumes) >= 5:
        recent5 = volumes[-5:]
        avg5 = sum(recent5) / 5 if recent5 else 0
        volume_5d_avg = _safe_val(avg5)
        # volume_signal: 최신 거래량 / 5일 평균 (직전 5봉 평균 대비 배수)
        # 최신 포함 평균 대신 직전 5봉 평균을 쓰는 게 신호 의미 명확
        if len(volumes) >= 6:
            prev5 = volumes[-6:-1]
            avg_prev5 = sum(prev5) / 5 if prev5 else 0
            if avg_prev5 > 0:
                volume_signal = _safe_val(round(cur_volume / avg_prev5, 2))
    if len(volumes) >= 20:
        recent20 = volumes[-20:]
        avg20 = sum(recent20) / 20 if recent20 else 0
        volume_20d_avg = _safe_val(avg20)

    # BB 위치 (Phase 2-1): (close - lower) / (upper - lower) × 100
    bb_position: Optional[float] = None
    bb_upper_cur = next((v for v in reversed(bb_upper) if v is not None), None)
    bb_lower_cur = next((v for v in reversed(bb_lower) if v is not None), None)
    if (
        bb_upper_cur is not None
        and bb_lower_cur is not None
        and bb_upper_cur > bb_lower_cur
        and cur_close is not None
    ):
        bb_position = _safe_val(round((cur_close - bb_lower_cur) / (bb_upper_cur - bb_lower_cur) * 100, 1))

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
        "volatility_target_k03": volatility_target_k03,
        "volatility_target_k05": volatility_target_k05,
        "volatility_target_k07": volatility_target_k07,
        "current_signals": {
            "macd_cross": macd_cross,
            "rsi_signal": rsi_signal,
            "rsi_value": rsi_cur,
            "stoch_signal": stoch_signal,
            "stoch_k": k_cur,
            "above_ma20": above_ma20,
            "ma5": ma5_cur,
            "ma20": ma20_cur,
            "ma60": ma60_cur,
            "ma_alignment": ma_alignment,
            "atr": _safe_val(atr_cur),
            "current_price": _safe_val(cur_close),
            "volatility_target_k03": volatility_target_k03,
            "volatility_target_k05": volatility_target_k05,
            "volatility_target_k07": volatility_target_k07,
            # Phase 2-1 신규
            "volume_signal": volume_signal,
            "volume_5d_avg": volume_5d_avg,
            "volume_20d_avg": volume_20d_avg,
            "bb_position": bb_position,
        },
    }

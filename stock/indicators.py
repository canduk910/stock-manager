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
    """지수이동평균 (Exponential Moving Average).

    공식: EMA_t = price_t × k + EMA_(t-1) × (1 - k)
    여기서 k = 2 / (period + 1) (smoothing factor).

    초기 period개 데이터는 SMA(단순이동평균)로 시드값을 설정한 뒤,
    이후부터 EMA 공식을 적용한다. 이는 업계 표준 초기화 방법.

    MACD 계산에서 EMA(12), EMA(26), Signal(9)에 사용.
    """
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
    """단순이동평균 (Simple Moving Average).

    최근 period개 값의 산술평균. MA5/MA20/MA60 및 볼린저밴드 중심선에 사용.
    period-1개 미만의 초기 구간은 None 반환.
    """
    result: list[Optional[float]] = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1:i + 1]) / period
    return result


def _rsi(closes: list[float], period: int = 14) -> list[Optional[float]]:
    """Wilder's RSI (Relative Strength Index).

    Wilder 방식 RSI 계산:
      1. 초기 avg_gain/avg_loss: 최초 period개 상승/하락폭의 SMA
      2. 이후 smoothing: avg = (prev_avg × (period-1) + current) / period
         이는 Wilder의 EMA smoothing으로, 일반 EMA(k=2/(n+1))와 다름
      3. RS = avg_gain / avg_loss
      4. RSI = 100 - (100 / (1 + RS))

    기본 period=14 (업계 표준, Wilder 원저).
    avg_loss=0(연속 상승)이면 RS=100 → RSI=100.
    시그널 매핑: RSI ≥ 70 → overbought, RSI ≤ 30 → oversold, 그 외 neutral.
    """
    result: list[Optional[float]] = [None] * len(closes)
    if len(closes) <= period:
        return result
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    # 초기값: 최초 period개의 SMA
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(closes)):
        if i > period:
            # Wilder smoothing: 이전 평균에 (period-1) 가중, 현재값에 1 가중
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        result[i] = 100 - (100 / (1 + rs))

    return result


def _stoch(highs: list[float], lows: list[float], closes: list[float], k_period: int = 14, d_period: int = 3):
    """Stochastic Oscillator %K, %D.

    공식:
      %K = (종가 - k_period일 최저가) / (k_period일 최고가 - k_period일 최저가) × 100
      %D = %K의 d_period일 SMA (시그널 라인)

    기본 파라미터: k_period=14, d_period=3 (업계 표준).
    최고가=최저가(변동 없음)인 경우 %K=50.0 (중립값).
    시그널 매핑: %K ≥ 80 → overbought, %K ≤ 20 → oversold.
    """
    n = len(closes)
    k_vals: list[Optional[float]] = [None] * n
    for i in range(k_period - 1, n):
        h = max(highs[i - k_period + 1:i + 1])
        lo = min(lows[i - k_period + 1:i + 1])
        if h == lo:
            k_vals[i] = 50.0
        else:
            k_vals[i] = (closes[i] - lo) / (h - lo) * 100

    # %D = SMA(d_period) of %K. None이 아닌 유효값만 대상으로 계산.
    d_vals: list[Optional[float]] = [None] * n
    valid_k = [(i, v) for i, v in enumerate(k_vals) if v is not None]
    for j in range(d_period - 1, len(valid_k)):
        chunk = [valid_k[j - d_period + 1 + x][1] for x in range(d_period)]
        idx = valid_k[j][0]
        d_vals[idx] = sum(chunk) / d_period

    return k_vals, d_vals


def _bollinger(closes: list[float], period: int = 20, sigma: float = 2.0):
    """볼린저밴드 (Bollinger Bands).

    공식:
      중심선(mid) = SMA(period)
      상단(upper) = mid + sigma × 표준편차
      하단(lower) = mid - sigma × 표준편차

    기본: period=20, sigma=2.0 (볼린저 원저 기본값).
    모집단 표준편차 사용 (N으로 나눔, N-1이 아님) — 볼린저 원저 방식.
    bb_position: (close - lower) / (upper - lower) × 100 으로
    0=하단 터치, 100=상단 터치 위치를 나타냄.
    """
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

    True Range = max(당일 고가-저가, |당일 고가-전일 종가|, |당일 저가-전일 종가|)
    ATR = TR의 Wilder smoothing 평균 (초기 period개는 SMA, 이후 EMA)

    기본 period=14 (Wilder 원저).
    변동성 돌파 목표가와 포지션 사이징에 활용.
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
    """계산 결과를 소수점 4자리로 반올림. NaN/Inf는 None 변환.

    float 연산 중 발생할 수 있는 NaN(0/0), Inf(overflow)를
    JSON 직렬화 전에 안전하게 처리한다.
    """
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

    # MACD (12, 26, 9): 업계 표준 파라미터
    # MACD Line = EMA(12) - EMA(26), Signal Line = EMA(9) of MACD Line
    # Histogram = MACD Line - Signal Line
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

    # 변동성 돌파 목표가 (Larry Williams 전략):
    # 목표가 = 당일 시가 + 전일 (고가 - 저가) × K
    # K값별 의미:
    #   K=0.3: 보수적 (좁은 돌파 기준, 진입 빈도 높음)
    #   K=0.5: 표준 (래리 윌리엄스 원래 K값)
    #   K=0.7: 공격적 (넓은 돌파 기준, 확실한 돌파만 진입)
    volatility_target = None
    volatility_target_k03 = volatility_target_k05 = volatility_target_k07 = None
    if len(ohlcv) >= 2:
        range_val = ohlcv[-2]["high"] - ohlcv[-2]["low"]  # 전일 변동폭
        open_cur  = ohlcv[-1]["open"]                      # 당일 시가
        volatility_target_k03 = _safe_val(open_cur + range_val * 0.3)
        volatility_target_k05 = _safe_val(open_cur + range_val * 0.5)
        volatility_target_k07 = _safe_val(open_cur + range_val * 0.7)
        volatility_target = volatility_target_k05

    # 현재 시그널 요약
    cur_close = closes[-1] if closes else 0

    # MACD 크로스 판정 (마지막 2봉 비교):
    # golden cross: MACD가 Signal을 아래→위로 돌파 (매수 신호)
    # dead cross: MACD가 Signal을 위→아래로 돌파 (매도 신호)
    # none: 크로스 없음
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

    # RSI 시그널 매핑: ≥70 과매수(overbought), ≤30 과매도(oversold), 그 외 중립(neutral)
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

    # MA 배열 판정:
    # 정배열: MA5 > MA20 > MA60 (상승 추세, 매수 우위)
    # 역배열: MA5 < MA20 < MA60 (하락 추세, 매도 우위)
    # 혼합: 그 외 (횡보 또는 추세 전환 중)
    ma_alignment = "혼합"
    if all(v is not None for v in [ma5_cur, ma20_cur, ma60_cur]):
        if ma5_cur > ma20_cur > ma60_cur:
            ma_alignment = "정배열"
        elif ma5_cur < ma20_cur < ma60_cur:
            ma_alignment = "역배열"

    # 거래량 신호 (Phase 2-1):
    # volume_signal = 최신 거래량 / 직전 5봉 평균 거래량 (배수)
    #   > 1.5: 거래량 급증 (관심 집중, 돌파 가능)
    #   < 0.7: 거래량 급감 (관심 이탈, 횡보)
    #   ≈ 1.0: 보통
    # 최신봉을 포함하지 않는 직전 5봉 평균을 사용해야 신호 의미가 명확함
    volume_5d_avg: Optional[float] = None
    volume_20d_avg: Optional[float] = None
    volume_signal: Optional[float] = None
    cur_volume = volumes[-1] if volumes else 0
    if len(volumes) >= 5:
        recent5 = volumes[-5:]
        avg5 = sum(recent5) / 5 if recent5 else 0
        volume_5d_avg = _safe_val(avg5)
        # volume_signal: 최신 거래량 / 직전 5봉 평균 대비 배수
        if len(volumes) >= 6:
            prev5 = volumes[-6:-1]
            avg_prev5 = sum(prev5) / 5 if prev5 else 0
            if avg_prev5 > 0:
                volume_signal = _safe_val(round(cur_volume / avg_prev5, 2))
    if len(volumes) >= 20:
        recent20 = volumes[-20:]
        avg20 = sum(recent20) / 20 if recent20 else 0
        volume_20d_avg = _safe_val(avg20)

    # BB 위치 (Phase 2-1): 볼린저밴드 내 종가 위치 (0~100%)
    # 0 = 하단밴드 터치, 50 = 중심선, 100 = 상단밴드 터치
    # 공식: (close - lower) / (upper - lower) × 100
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

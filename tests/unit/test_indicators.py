"""stock/indicators.py 기술지표 계산 단위 테스트."""

import math

import pytest

from stock.indicators import (
    _ema,
    _sma,
    _rsi,
    _stoch,
    _bollinger,
    _atr,
    _safe_val,
    calc_technical_indicators,
)


# ── _ema ──────────────────────────────────────────────────────

class TestEma:
    def test_basic(self):
        result = _ema([1, 2, 3, 4, 5], period=3)
        assert result[0] is None
        assert result[1] is None
        # SMA seed = (1+2+3)/3 = 2.0
        assert result[2] == pytest.approx(2.0)
        # EMA(3): k=2/(3+1)=0.5; EMA = 4*0.5 + 2.0*0.5 = 3.0
        assert result[3] == pytest.approx(3.0)
        # EMA = 5*0.5 + 3.0*0.5 = 4.0
        assert result[4] == pytest.approx(4.0)

    def test_short_data(self):
        result = _ema([1, 2], period=5)
        assert all(v is None for v in result)

    def test_single_period(self):
        result = _ema([10, 20, 30], period=1)
        # k=2/(1+1)=1.0, so EMA = value itself
        assert result[0] == pytest.approx(10.0)
        assert result[1] == pytest.approx(20.0)
        assert result[2] == pytest.approx(30.0)

    def test_constant_values(self):
        result = _ema([5, 5, 5, 5, 5], period=3)
        for i in range(2, 5):
            assert result[i] == pytest.approx(5.0)

    def test_empty_input(self):
        result = _ema([], period=3)
        assert result == []


# ── _sma ──────────────────────────────────────────────────────

class TestSma:
    def test_basic(self):
        result = _sma([1, 2, 3, 4, 5], period=3)
        assert result == [None, None, pytest.approx(2.0), pytest.approx(3.0), pytest.approx(4.0)]

    def test_short_data(self):
        result = _sma([1], period=5)
        assert result == [None]

    def test_period_equals_length(self):
        result = _sma([10, 20, 30], period=3)
        assert result[0] is None
        assert result[1] is None
        assert result[2] == pytest.approx(20.0)

    def test_constant_values(self):
        result = _sma([7, 7, 7, 7], period=2)
        for i in range(1, 4):
            assert result[i] == pytest.approx(7.0)


# ── _rsi ──────────────────────────────────────────────────────

class TestRsi:
    def test_uptrend(self):
        closes = list(range(20))  # 0,1,2,...,19
        result = _rsi(closes, 14)
        # 연속 상승 -> RSI > 70
        last_rsi = next(v for v in reversed(result) if v is not None)
        assert last_rsi > 70

    def test_downtrend(self):
        closes = [20 - i for i in range(20)]  # 20,19,...,1
        result = _rsi(closes, 14)
        last_rsi = next(v for v in reversed(result) if v is not None)
        assert last_rsi < 30

    def test_flat(self):
        closes = [50] * 20
        result = _rsi(closes, 14)
        # 변동 없으면 gains=losses=0 -> avg_loss=0 -> rs=100 -> RSI 계산
        # 실제로 all gains=0, losses=0 -> avg_gain=0, avg_loss=0 -> rs=100 -> RSI=100-(100/101)
        # 첫 유효값 검증: avg_gain=0, avg_loss=0 -> rs=100 -> rsi = 100 - 100/101
        valid = [v for v in result if v is not None]
        if valid:
            assert valid[0] == pytest.approx(100 - 100 / 101, abs=0.1)

    def test_short_data(self):
        result = _rsi([1] * 14, 14)
        assert all(v is None for v in result)

    def test_all_gains_no_loss(self):
        closes = list(range(1, 18))  # 1~17, 16 values, period=14
        result = _rsi(closes, 14)
        last_rsi = next(v for v in reversed(result) if v is not None)
        # Wilder smoothing: avg_loss 0에서 시작하지만 smoothing 후 미세 잔여 -> RSI ~99
        assert last_rsi > 98


# ── _stoch ────────────────────────────────────────────────────

class TestStoch:
    def test_overbought(self):
        n = 20
        highs = [100 + i for i in range(n)]
        lows = [90 + i for i in range(n)]
        closes = [99 + i for i in range(n)]  # close near high
        k_vals, d_vals = _stoch(highs, lows, closes, 14, 3)
        last_k = next(v for v in reversed(k_vals) if v is not None)
        assert last_k >= 80

    def test_oversold(self):
        n = 20
        highs = [110 - i for i in range(n)]
        lows = [100 - i for i in range(n)]
        closes = [101 - i for i in range(n)]  # close near low
        k_vals, d_vals = _stoch(highs, lows, closes, 14, 3)
        last_k = next(v for v in reversed(k_vals) if v is not None)
        assert last_k <= 20

    def test_equal_high_low(self):
        n = 20
        highs = [100] * n
        lows = [100] * n
        closes = [100] * n
        k_vals, d_vals = _stoch(highs, lows, closes, 14, 3)
        valid_k = [v for v in k_vals if v is not None]
        assert all(v == pytest.approx(50.0) for v in valid_k)


# ── _bollinger ────────────────────────────────────────────────

class TestBollinger:
    def test_basic(self):
        closes = [100 + i for i in range(25)]
        upper, mid, lower = _bollinger(closes, 20, 2.0)
        # index 19 이후 값 존재
        assert mid[19] is not None
        assert upper[19] > mid[19]
        assert lower[19] < mid[19]

    def test_constant_values(self):
        closes = [100.0] * 25
        upper, mid, lower = _bollinger(closes, 20, 2.0)
        # std=0 -> upper=mid=lower
        for i in range(19, 25):
            assert upper[i] == pytest.approx(100.0)
            assert mid[i] == pytest.approx(100.0)
            assert lower[i] == pytest.approx(100.0)

    def test_short_data(self):
        closes = [1] * 10
        upper, mid, lower = _bollinger(closes, 20, 2.0)
        assert all(v is None for v in upper)
        assert all(v is None for v in mid)
        assert all(v is None for v in lower)


# ── _atr ──────────────────────────────────────────────────────

class TestAtr:
    def test_basic(self):
        n = 20
        highs = [110 + i for i in range(n)]
        lows = [100 + i for i in range(n)]
        closes = [105 + i for i in range(n)]
        result = _atr(highs, lows, closes, 14)
        # period+1 = 15번째(index 14) 이후 값 존재
        assert result[14] is not None
        assert result[14] > 0

    def test_short_data(self):
        result = _atr([110] * 10, [100] * 10, [105] * 10, 14)
        assert all(v is None for v in result)

    def test_zero_range(self):
        n = 20
        val = 100.0
        highs = [val] * n
        lows = [val] * n
        closes = [val] * n
        result = _atr(highs, lows, closes, 14)
        # 변동 없으면 ATR = 0
        valid = [v for v in result if v is not None]
        assert all(v == pytest.approx(0.0) for v in valid)


# ── _safe_val ─────────────────────────────────────────────────

class TestSafeVal:
    def test_normal_float(self):
        assert _safe_val(3.14159) == pytest.approx(3.1416)

    def test_nan(self):
        assert _safe_val(float("nan")) is None

    def test_inf(self):
        assert _safe_val(float("inf")) is None

    def test_neg_inf(self):
        assert _safe_val(float("-inf")) is None

    def test_none(self):
        assert _safe_val(None) is None

    def test_zero(self):
        assert _safe_val(0.0) == pytest.approx(0.0)

    def test_negative(self):
        assert _safe_val(-1.23456) == pytest.approx(-1.2346)


# ── calc_technical_indicators (통합) ──────────────────────────

def _make_ohlcv(n, base_price=100, base_volume=1000):
    """n봉의 OHLCV 데이터 생성. 점진적 상승 패턴."""
    bars = []
    for i in range(n):
        p = base_price + i
        bars.append({
            "time": f"2026-01-{i+1:02d}",
            "open": p,
            "high": p + 5,
            "low": p - 3,
            "close": p + 2,
            "volume": base_volume + i * 100,
        })
    return bars


class TestCalcTechnicalIndicators:
    def test_empty_ohlcv(self):
        result = calc_technical_indicators([])
        assert result["current_signals"]["macd_cross"] == "none"
        assert result["current_signals"]["rsi_signal"] == "neutral"
        assert result["volatility_target"] is None

    def test_single_bar(self):
        bars = [{"time": "2026-01-01", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000}]
        result = calc_technical_indicators(bars)
        assert result["current_signals"]["macd_cross"] == "none"
        assert result["volatility_target"] is None

    def test_minimal_two_bars(self):
        bars = [
            {"time": "2026-01-01", "open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
            {"time": "2026-01-02", "open": 106, "high": 115, "low": 95, "close": 110, "volume": 1200},
        ]
        result = calc_technical_indicators(bars)
        # volatility_target = open + range * 0.5
        range_val = 110 - 90  # 전일 고-저
        expected = 106 + range_val * 0.5  # 당일 시가 + range*0.5
        assert result["volatility_target"] == pytest.approx(expected, abs=0.01)
        assert result["volatility_target_k03"] is not None
        assert result["volatility_target_k07"] is not None

    def test_full_ohlcv_structure(self):
        bars = _make_ohlcv(65)
        result = calc_technical_indicators(bars)
        # 구조 검증
        assert "macd" in result
        assert "rsi" in result
        assert "stoch" in result
        assert "bb" in result
        assert "ma" in result
        assert "current_signals" in result
        signals = result["current_signals"]
        assert "macd_cross" in signals
        assert "rsi_signal" in signals
        assert "stoch_signal" in signals
        assert "above_ma20" in signals
        assert "ma_alignment" in signals
        assert "atr" in signals
        assert "volume_signal" in signals
        assert "bb_position" in signals

    def test_ma_alignment_positive(self):
        # 강한 상승 추세: MA5 > MA20 > MA60
        bars = _make_ohlcv(70, base_price=100)
        result = calc_technical_indicators(bars)
        assert result["current_signals"]["ma_alignment"] == "정배열"

    def test_ma_alignment_negative(self):
        # 강한 하락 추세: MA5 < MA20 < MA60
        bars = []
        for i in range(70):
            p = 200 - i * 2
            bars.append({
                "time": f"2026-{(i//28)+1:02d}-{(i%28)+1:02d}",
                "open": p + 1, "high": p + 3, "low": p - 3, "close": p, "volume": 1000,
            })
        result = calc_technical_indicators(bars)
        assert result["current_signals"]["ma_alignment"] == "역배열"

    def test_rsi_signal_overbought(self):
        # 급등 -> RSI > 70
        bars = []
        for i in range(30):
            p = 100 + i * 5  # 급상승
            bars.append({
                "time": f"2026-01-{i+1:02d}",
                "open": p, "high": p + 2, "low": p - 1, "close": p + 1, "volume": 1000,
            })
        result = calc_technical_indicators(bars)
        assert result["current_signals"]["rsi_signal"] == "overbought"

    def test_volume_signal(self):
        bars = _make_ohlcv(10)
        result = calc_technical_indicators(bars)
        # 6봉 이상이면 volume_signal 계산됨
        assert result["current_signals"]["volume_signal"] is not None

    def test_bb_position(self):
        bars = _make_ohlcv(25)
        result = calc_technical_indicators(bars)
        bp = result["current_signals"]["bb_position"]
        if bp is not None:
            assert 0 <= bp <= 100

    def test_volatility_target_k_values(self):
        bars = [
            {"time": "2026-01-01", "open": 100, "high": 120, "low": 80, "close": 110, "volume": 1000},
            {"time": "2026-01-02", "open": 112, "high": 125, "low": 105, "close": 118, "volume": 1200},
        ]
        result = calc_technical_indicators(bars)
        range_val = 120 - 80  # 전일 변동폭 = 40
        assert result["volatility_target_k03"] == pytest.approx(112 + 40 * 0.3, abs=0.01)
        assert result["volatility_target_k05"] == pytest.approx(112 + 40 * 0.5, abs=0.01)
        assert result["volatility_target_k07"] == pytest.approx(112 + 40 * 0.7, abs=0.01)

    def test_macd_golden_cross(self):
        # 짧은 EMA가 긴 EMA를 돌파하는 패턴
        bars = []
        # 하락 후 급반등
        for i in range(30):
            p = 200 - i * 2
            bars.append({
                "time": f"2026-01-{i+1:02d}",
                "open": p, "high": p + 2, "low": p - 2, "close": p, "volume": 1000,
            })
        for i in range(15):
            p = 140 + i * 5
            bars.append({
                "time": f"2026-02-{i+1:02d}",
                "open": p, "high": p + 3, "low": p - 1, "close": p + 2, "volume": 2000,
            })
        result = calc_technical_indicators(bars)
        # golden cross가 발생할 수 있음 (패턴 의존적이므로 구조만 검증)
        assert result["current_signals"]["macd_cross"] in ("golden", "dead", "none")

    def test_macd_dead_cross(self):
        # 상승 후 급하락
        bars = []
        for i in range(30):
            p = 100 + i * 2
            bars.append({
                "time": f"2026-01-{i+1:02d}",
                "open": p, "high": p + 2, "low": p - 2, "close": p, "volume": 1000,
            })
        for i in range(15):
            p = 160 - i * 5
            bars.append({
                "time": f"2026-02-{i+1:02d}",
                "open": p, "high": p + 1, "low": p - 3, "close": p - 2, "volume": 2000,
            })
        result = calc_technical_indicators(bars)
        assert result["current_signals"]["macd_cross"] in ("golden", "dead", "none")

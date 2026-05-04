"""R3 (2026-05-04): 섹터 상대평가 산점도 헬퍼 단위 테스트."""

from stock.macro_fetcher import (
    _compute_sma20_trend_days,
    _compute_intensity_zscore,
)


def test_compute_sma20_trend_days_uptrend():
    """상승 추세: 종가 1..100 → 양수 + 충분히 큼."""
    closes = list(range(1, 101))
    days = _compute_sma20_trend_days(closes)
    assert days > 0
    assert days <= 365


def test_compute_sma20_trend_days_downtrend():
    """하락 추세: 종가 100..1 → 음수."""
    closes = list(range(100, 0, -1))
    days = _compute_sma20_trend_days(closes)
    assert days < 0
    assert days >= -365


def test_compute_sma20_trend_days_insufficient_data():
    """25일 미만 → 0."""
    assert _compute_sma20_trend_days([1.0, 2.0, 3.0]) == 0
    assert _compute_sma20_trend_days([]) == 0
    assert _compute_sma20_trend_days(None) == 0


def test_compute_sma20_trend_days_cap_365():
    """매우 긴 일관 추세도 ±365 cap."""
    closes = list(range(1, 2000))
    days = _compute_sma20_trend_days(closes)
    assert -365 <= days <= 365


def test_compute_intensity_zscore_basic():
    """기본 z-score: 평균 0, std=일정 → 정확한 표준화."""
    out = _compute_intensity_zscore([-0.2, -0.1, 0.0, 0.1, 0.2])
    # 분포 평균 0, std ≈ 0.1414 → -0.2 / 0.1414 ≈ -1.414
    assert abs(out[0] - (-1.414)) < 0.01
    assert abs(out[2] - 0.0) < 0.01
    assert abs(out[4] - 1.414) < 0.01


def test_compute_intensity_zscore_zero_std():
    """std=0 (모두 동일) → 모두 0."""
    out = _compute_intensity_zscore([0.5, 0.5, 0.5])
    assert out == [0.0, 0.0, 0.0]


def test_compute_intensity_zscore_with_none():
    """None 입력은 0.0으로 반환, 위치 유지."""
    out = _compute_intensity_zscore([0.1, None, 0.3])
    assert len(out) == 3
    assert out[1] == 0.0


def test_compute_intensity_zscore_caps_at_3():
    """극단치도 ±3 cap."""
    # 1개만 매우 크면 z-score 절댓값 큼
    out = _compute_intensity_zscore([0.0, 0.0, 0.0, 0.0, 0.0, 100.0])
    assert max(abs(v) for v in out) <= 3.0


def test_compute_intensity_zscore_single_value():
    """n<2 → 모두 0."""
    assert _compute_intensity_zscore([0.5]) == [0.0]
    assert _compute_intensity_zscore([]) == []

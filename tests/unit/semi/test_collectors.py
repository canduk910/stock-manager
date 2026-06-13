"""Collector base + 5종 수집기 단위 테스트."""

from stock.semi_collectors.base import (
    CollectorResult,
    apply_outlier_guard,
    pct_change_or_none,
)


# ── CollectorResult ───────────────────────────────────────


def test_collector_result_default_unit():
    r = CollectorResult(
        indicator_name="x",
        observed_at="2026-06-13",
        value=1.0,
        value_meta={},
        source="test",
    )
    assert r.value_meta["unit"] == "unknown"  # 강제 채움


def test_collector_result_preserves_explicit_unit():
    r = CollectorResult(
        indicator_name="memory_inventory",
        observed_at="2026-03-31",
        value=82.4,
        value_meta={"unit": "days", "samsung": {}},
        source="dart_fin",
    )
    assert r.value_meta["unit"] == "days"
    assert "samsung" in r.value_meta


# ── apply_outlier_guard ───────────────────────────────────


def test_outlier_guard_passes_within_threshold():
    # 5% 변동 → pct=30%면 가드 통과
    assert apply_outlier_guard(105.0, 100.0, pct=30.0) is True


def test_outlier_guard_rejects_excess_movement():
    # 50% 변동 → 격리
    assert apply_outlier_guard(150.0, 100.0, pct=30.0) is False


def test_outlier_guard_prev_none_passes():
    # 비교 불가 — 첫 데이터포인트는 가드 통과
    assert apply_outlier_guard(100.0, None) is True
    assert apply_outlier_guard(100.0, 0) is True


def test_outlier_guard_curr_none_rejects():
    # 불완전 데이터는 격리
    assert apply_outlier_guard(None, 100.0) is False


def test_outlier_guard_negative_prev():
    # 음수 prev (capex YoY%) — abs 비교
    assert apply_outlier_guard(-7.0, -5.0, pct=50.0) is True  # 40% 증가
    assert apply_outlier_guard(-10.0, -5.0, pct=50.0) is False  # 100% 증가


# ── pct_change_or_none ────────────────────────────────────


def test_pct_change_basic():
    assert pct_change_or_none(110.0, 100.0) == 10.0
    assert pct_change_or_none(80.0, 100.0) == -20.0


def test_pct_change_zero_prev():
    assert pct_change_or_none(100.0, 0) is None


def test_pct_change_none_inputs():
    assert pct_change_or_none(None, 100.0) is None
    assert pct_change_or_none(100.0, None) is None

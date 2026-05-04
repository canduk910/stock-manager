"""macro_regime 신용 통합 — F&G 보정(Phase 1) + 신용 오버라이드(Phase 2).

R2 (P1): hy_oas_percentile 한 단계 보정 + VIX 우선순위 보존.
R4 (P3): 신용 오버라이드(extreme_fear_accumulation / dual_extreme_selective / credit_greed_defensive).
"""

from __future__ import annotations

import pytest

from services.macro_regime import determine_regime


def _sentiment(vix=20.0, buffett=1.0, fg=50.0):
    return {
        "vix": {"value": vix},
        "buffett_indicator": {"ratio": buffett},
        "fear_greed": {"score": fg},
    }


# ── R2-3: F&G 보정 (Phase 1) ──────────────────────────────────

class TestCreditFgAdjustment:
    def test_fg_adjustment_extreme_fear_credit(self):
        """HY 백분위 95 → fg_level 한 단계 fear 쪽 강제."""
        # 기본: buffett normal + fg neutral=50 → fg_level=neutral → regime=cautious
        # +HY p95 → fg_level=fear → regime=selective
        result = determine_regime(
            _sentiment(vix=20.0, buffett=1.0, fg=50.0),
            hy_oas_percentile=95.0,
        )
        assert result["fg_level"] == "fear"
        assert result.get("credit_adjustment") == "fear_one_step"
        # normal+fear → selective
        assert result["regime"] == "selective"

    def test_fg_adjustment_extreme_greed_credit(self):
        """HY 백분위 5 → fg_level 한 단계 greed 쪽 강제."""
        result = determine_regime(
            _sentiment(vix=20.0, buffett=1.0, fg=50.0),
            hy_oas_percentile=5.0,
        )
        assert result["fg_level"] == "greed"
        assert result.get("credit_adjustment") == "greed_one_step"
        # normal+greed → cautious
        assert result["regime"] == "cautious"

    def test_no_adjustment_normal_percentile(self):
        """HY 백분위 50 → 보정 없음."""
        result = determine_regime(
            _sentiment(vix=20.0, buffett=1.0, fg=50.0),
            hy_oas_percentile=50.0,
        )
        assert result.get("credit_adjustment") is None
        assert result["fg_level"] == "neutral"

    def test_vix_override_priority(self):
        """VIX>35 + HY p<5 → VIX 우선(extreme_fear 유지)."""
        result = determine_regime(
            _sentiment(vix=40.0, buffett=1.0, fg=50.0),
            hy_oas_percentile=3.0,
        )
        # VIX > 35 → fg_level=extreme_fear 유지 (한 단계 greed 강제 무시)
        assert result["fg_level"] == "extreme_fear"


# ── R4-3: 신용 오버라이드 (Phase 2) ──────────────────────────

class TestCreditOverride:
    def test_credit_override_extreme_fear_accumulation(self):
        """hy_oas=11% + buffett=normal → regime=accumulation 강제."""
        result = determine_regime(
            _sentiment(vix=20.0, buffett=1.0, fg=50.0),
            hy_oas_percentile=98.0,
            hy_oas_value=11.0,
        )
        assert result["regime"] == "accumulation"
        assert result.get("credit_override") == "extreme_fear_accumulation"

    def test_credit_override_dual_extreme_selective(self):
        """hy_oas=11% + buffett=extreme → regime=selective (양방향 위기 완화)."""
        result = determine_regime(
            _sentiment(vix=20.0, buffett=2.0, fg=50.0),
            hy_oas_percentile=98.0,
            hy_oas_value=11.0,
        )
        assert result["regime"] == "selective"
        assert result.get("credit_override") == "extreme_fear_selective"

    def test_credit_greed_buffett_extreme_defensive(self):
        """hy_oas_percentile=3 + buffett=extreme → regime=defensive 강제."""
        result = determine_regime(
            _sentiment(vix=20.0, buffett=2.0, fg=50.0),
            hy_oas_percentile=3.0,
        )
        assert result["regime"] == "defensive"
        assert result.get("credit_override") == "credit_greed_defensive"

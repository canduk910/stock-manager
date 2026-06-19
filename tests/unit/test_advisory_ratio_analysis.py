"""advisory_service _collect_fundamental_kr/us ratio_analysis 통합 테스트 (REQ-SCREEN-02).

- 추가 외부 호출 0건 — 기존 수집 결과 재사용.
- KR: sector_tier 전파. US: general 고정.
- ratio_analysis 산출 실패 시 None + 로깅, fundamental 응답 전체는 정상 반환.
"""

from unittest.mock import patch

from services import advisory_service


def _fake_collected(sector_tier="general"):
    """compute_ratio_analysis가 정상 산출 가능한 최소 데이터."""
    return {
        "income_stmt": [
            {"revenue": 100, "operating_income": 20, "net_income": 15, "cogs": 60, "interest_expense": 2},
            {"revenue": 110, "operating_income": 22, "net_income": 17, "cogs": 66, "interest_expense": 2},
            {"revenue": 121, "operating_income": 25, "net_income": 20, "cogs": 70, "interest_expense": 2},
        ],
        "balance_sheet": [
            {"total_assets": 200, "current_assets": 120, "receivables": 40, "inventories": 30,
             "payables": 25, "total_liabilities": 80, "current_liabilities": 60,
             "short_term_debt": 10, "long_term_debt": 10, "total_equity": 120},
            {"total_assets": 220, "current_assets": 130, "receivables": 42, "inventories": 28,
             "payables": 24, "total_liabilities": 85, "current_liabilities": 62,
             "short_term_debt": 10, "long_term_debt": 10, "total_equity": 135},
            {"total_assets": 240, "current_assets": 140, "receivables": 44, "inventories": 26,
             "payables": 22, "total_liabilities": 90, "current_liabilities": 64,
             "short_term_debt": 10, "long_term_debt": 10, "total_equity": 150},
        ],
        "cashflow": [{"operating_cf": 18}, {"operating_cf": 20}, {"operating_cf": 23}],
        "metrics": {"oi_margin": 20.6, "roe": 13.3, "debt_ratio": 60, "current_ratio": 140},
        "sector_tier": sector_tier,
    }


def test_attach_ratio_analysis_success():
    """정상 데이터 → ratio_analysis.overall_score is not None."""
    collected = _fake_collected()
    out = advisory_service._attach_ratio_analysis(collected)
    assert "ratio_analysis" in out
    assert out["ratio_analysis"] is not None
    assert out["ratio_analysis"]["overall_score"] is not None
    # 다른 키 불변
    assert out["income_stmt"] is collected["income_stmt"]


def test_attach_ratio_analysis_uses_sector_tier():
    """sector_tier 전파 — bank_holding 시 activity N/A."""
    collected = _fake_collected(sector_tier="bank_holding")
    out = advisory_service._attach_ratio_analysis(collected)
    assert out["ratio_analysis"]["sector_tier"] == "bank_holding"
    assert out["ratio_analysis"]["axes"]["activity"]["applicable"] is False


def test_attach_ratio_analysis_exception_isolated():
    """compute_ratio_analysis 예외 → ratio_analysis None, 나머지 키 정상 (부분 실패 격리)."""
    collected = _fake_collected()
    with patch.object(advisory_service.financial_ratios, "compute_ratio_analysis",
                      side_effect=RuntimeError("boom")):
        out = advisory_service._attach_ratio_analysis(collected)
    assert out["ratio_analysis"] is None
    assert out["income_stmt"] is collected["income_stmt"]
    assert out["metrics"] is collected["metrics"]


def test_attach_ratio_analysis_no_extra_external_calls():
    """추가 외부 호출 0건 — compute_ratio_analysis는 순수 함수, 호출 1회만."""
    collected = _fake_collected()
    with patch.object(advisory_service.financial_ratios, "compute_ratio_analysis",
                      wraps=advisory_service.financial_ratios.compute_ratio_analysis) as spy:
        advisory_service._attach_ratio_analysis(collected)
    assert spy.call_count == 1

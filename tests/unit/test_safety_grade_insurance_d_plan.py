"""safety_grade.compute_insurance_grade (B-2 D안) 회귀 테스트.

2026-05-10 Phase B-2: B-1 진입금지 가드 → 정식 D안 4지표 12점 등급 위임.
MarginAnalyst 자문(2026-05-09):
- ROE / 자기자본비율(자본/자산, K-ICS 기준) / 매출성장률(보험료 CAGR) / 배당안정성
- 비례 환산 12 → 28점, A≥10.3 / B+≥8.6 / B≥6.9 / C≥5.1 / D<5.1
- Graham/부채비율/유동비율/FCF 제외 (보험사 본질상 적용 불가)
"""

import pytest

from services.safety_grade import (
    compute_insurance_grade,
    compute_grade_7point,
    _score_insurance_roe,
    _score_insurance_equity_ratio,
    _score_dividend_stability,
)


# ── 단위 점수 함수 ─────────────────────────────────────────────────

def test_roe_thresholds():
    """ROE 임계값 — 일반과 동일 (15/10/5)."""
    assert _score_insurance_roe(20.0) == 4
    assert _score_insurance_roe(12.0) == 3
    assert _score_insurance_roe(7.0) == 2
    assert _score_insurance_roe(3.0) == 1
    assert _score_insurance_roe(None) == 2  # 중립


def test_equity_ratio_insurance_thresholds():
    """보험사 자기자본비율 임계값 — K-ICS 기준 >15/10/5."""
    # 자본 200억 / 자산 1000억 = 20%
    assert _score_insurance_equity_ratio(200, 1000) == 4
    # 자본 120억 / 자산 1000억 = 12%
    assert _score_insurance_equity_ratio(120, 1000) == 3
    # 자본 80억 / 자산 1000억 = 8%
    assert _score_insurance_equity_ratio(80, 1000) == 2
    # 자본 30억 / 자산 1000억 = 3%
    assert _score_insurance_equity_ratio(30, 1000) == 1


def test_equity_ratio_handles_none():
    """None/0 입력 graceful."""
    assert _score_insurance_equity_ratio(None, 1000) == 2
    assert _score_insurance_equity_ratio(100, None) == 2
    assert _score_insurance_equity_ratio(100, 0) == 2


def test_dividend_stability_3y_positive():
    """3년 연속 순이익 양수 → 4점."""
    income = [
        {"year": 2023, "net_income": 1_000_000_000},
        {"year": 2024, "net_income": 1_200_000_000},
        {"year": 2025, "net_income": 1_500_000_000},
    ]
    assert _score_dividend_stability(income) == 4


def test_dividend_stability_zero_years():
    """전 연도 적자 → 1점."""
    income = [
        {"year": 2023, "net_income": -100_000_000},
        {"year": 2024, "net_income": -200_000_000},
        {"year": 2025, "net_income": -50_000_000},
    ]
    assert _score_dividend_stability(income) == 1


def test_dividend_stability_empty():
    """빈 income_stmt → 1점."""
    assert _score_dividend_stability([]) == 1


# ── compute_insurance_grade 통합 ───────────────────────────────────

def _high_quality_bs(equity_ratio_pct=15.0):
    """우량 보험사 BS — 자본 1조5천억 / 자산 10조 = 15%."""
    return [{
        "year": 2025,
        "total_assets": 10_000_000_000_000,
        "total_equity": int(10_000_000_000_000 * equity_ratio_pct / 100),
        "insurance_liabilities": 8_000_000_000_000,  # 보험업 감지 트리거 (참고)
    }]


def _high_growth_income():
    """매출 CAGR ~12% 우량 보험사."""
    return [
        {"year": 2023, "revenue": 14_000_000_000_000, "net_income": 1_500_000_000_000},
        {"year": 2024, "revenue": 16_000_000_000_000, "net_income": 1_700_000_000_000},
        {"year": 2025, "revenue": 17_500_000_000_000, "net_income": 1_900_000_000_000},
    ]


def test_top_grade_insurance_company_gets_a():
    """우량 보험사 (ROE 20% / 자본 18% / CAGR 12% / 3년 흑자) → A."""
    metrics = {"roe": 20.0}
    bs = _high_quality_bs(equity_ratio_pct=18.0)
    income = _high_growth_income()
    result = compute_insurance_grade(metrics, bs, [], income)
    assert result["grade"] == "A"
    assert result["grade_factor"] == 1.0
    assert result["valid_entry"] is True
    assert result["details"]["industry_hint"] == "insurance"
    assert result["details"]["method"] == "insurance_4metric_12point"


def test_mid_grade_insurance_company_gets_b():
    """중급 보험사 (ROE 8% / 자본 8% / CAGR 3% / 3년 흑자) → B 또는 C."""
    metrics = {"roe": 8.0}
    bs = _high_quality_bs(equity_ratio_pct=8.0)
    income = [
        {"year": 2023, "revenue": 10_000_000_000_000, "net_income": 500_000_000_000},
        {"year": 2024, "revenue": 10_300_000_000_000, "net_income": 520_000_000_000},
        {"year": 2025, "revenue": 10_600_000_000_000, "net_income": 530_000_000_000},
    ]
    result = compute_insurance_grade(metrics, bs, [], income)
    # ROE=2점 + equity=2점 + cagr=2점(0~5%) + dividend=4점 = 10/16
    # → 12점 환산 = 7.5 → B (≥6.9)
    assert result["grade"] in ("B", "C")
    assert result["valid_entry"] is True


def test_poor_insurance_company_gets_d():
    """부실 보험사 (ROE 2% / 자본 3% / CAGR -5% / 적자) → D."""
    metrics = {"roe": 2.0}
    bs = [{"year": 2025, "total_assets": 10_000_000_000_000,
           "total_equity": 300_000_000_000, "insurance_liabilities": 9_000_000_000_000}]
    income = [
        {"year": 2023, "revenue": 12_000_000_000_000, "net_income": -100_000_000_000},
        {"year": 2024, "revenue": 11_000_000_000_000, "net_income": -200_000_000_000},
        {"year": 2025, "revenue": 10_500_000_000_000, "net_income": -150_000_000_000},
    ]
    result = compute_insurance_grade(metrics, bs, [], income)
    assert result["grade"] == "D"
    assert result["grade_factor"] == 0.0
    assert result["valid_entry"] is False


def test_excluded_metrics_documented():
    """제외 지표 명시 — Graham/부채/유동/FCF."""
    result = compute_insurance_grade({}, _high_quality_bs(), [], _high_growth_income())
    excluded = result["details"]["excluded"]
    assert "graham_discount" in excluded
    assert "debt_ratio" in excluded
    assert "current_ratio" in excluded
    assert "fcf_trend" in excluded


def test_response_shape_compatible_with_7point():
    """compute_grade_7point과 동일 응답 키 (호출자 호환)."""
    result = compute_insurance_grade({}, _high_quality_bs(), [], _high_growth_income())
    for key in ("score", "grade", "grade_factor", "valid_entry", "details"):
        assert key in result


def test_compute_grade_7point_delegates_to_insurance():
    """compute_grade_7point 진입부에서 보험업 감지 시 D안 위임."""
    metrics = {"roe": 15.0, "per": 8.0, "pbr": 0.8}
    bs = _high_quality_bs(equity_ratio_pct=12.0)
    income = _high_growth_income()
    result = compute_grade_7point(metrics, bs, [], income)
    # 보험업 D안 응답 — industry_hint=insurance + method 명시
    assert result["details"].get("industry_hint") == "insurance"
    assert result["details"].get("method") == "insurance_4metric_12point"
    # 일반 7점 details 키(`debt_ratio`/`pbr` 등)는 부재
    assert "debt_ratio" not in result["details"]


def test_compute_grade_7point_general_unchanged():
    """일반 제조업 BS는 기존 7점 흐름 (회귀 0건)."""
    metrics = {"roe": 12.0, "per": 10.0, "pbr": 1.0}
    bs = [{
        "year": 2025,
        "total_assets": 1_000_000_000_000,
        "total_equity": 600_000_000_000,
        "total_liabilities": 400_000_000_000,
        "current_assets": 500_000_000_000,
        "current_liabilities": 200_000_000_000,
        # insurance_* 키 자체 없음
    }]
    income = [
        {"year": 2023, "revenue": 5_000_000_000_000, "net_income": 500_000_000_000},
        {"year": 2024, "revenue": 5_500_000_000_000, "net_income": 600_000_000_000},
    ]
    result = compute_grade_7point(metrics, bs, [], income)
    assert result["details"].get("method") != "insurance_4metric_12point"
    assert result["details"].get("industry_hint") != "insurance"
    # 일반 7점 키 존재
    assert "debt_ratio" in result["details"]

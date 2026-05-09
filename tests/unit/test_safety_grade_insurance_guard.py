"""safety_grade.compute_grade_7point 보험업 라우팅 회귀 테스트.

2026-05-09 Phase B-1: 보험업 감지 시 일반 7점 우회 (단순 D 가드).
2026-05-10 Phase B-2: 가드 → compute_insurance_grade(D안 4지표 12점) 위임으로 진화.

본 테스트는 "보험업 BS는 일반 7점 흐름을 우회한다" 영구 의도를 검증하며,
B-1/B-2 응답 차이(D 강제 → 정식 등급)는 industry_hint + method 키로 식별.
"""

from services.safety_grade import compute_grade_7point


def test_insurance_company_routes_to_insurance_grade():
    """BS에 insurance_liabilities 존재 시 일반 7점 우회 + D안 위임."""
    balance_sheet = [{
        "year": 2024,
        "total_assets": 50_000_000_000_000,
        "total_equity": 6_000_000_000_000,
        "insurance_liabilities": 30_000_000_000_000,  # 책임준비금
    }]
    result = compute_grade_7point(
        metrics={"per": 8.0, "pbr": 0.7, "roe": 12.0},
        balance_sheet=balance_sheet,
        cashflow=[],
        income_stmt=[],
    )
    # B-2 D안 위임 확인 — industry_hint + method 명시
    assert result["details"].get("industry_hint") == "insurance"
    assert result["details"].get("method") == "insurance_4metric_12point"
    # 일반 7점 키(`debt_ratio`/`pbr` 등)는 응답에 없음
    assert "debt_ratio" not in result["details"]
    # 응답 shape는 일반과 호환
    assert "grade" in result and "score" in result and "valid_entry" in result


def test_insurance_assets_alone_triggers_routing():
    """insurance_assets만 있어도 보험업 감지 (재보험계약자산 등)."""
    balance_sheet = [{
        "year": 2024,
        "total_assets": 10_000_000_000_000,
        "insurance_assets": 500_000_000_000,
    }]
    result = compute_grade_7point(
        metrics={}, balance_sheet=balance_sheet, cashflow=[], income_stmt=[],
    )
    assert result["details"].get("industry_hint") == "insurance"
    assert result["details"].get("method") == "insurance_4metric_12point"


def test_insurance_zero_value_still_treated_as_general():
    """insurance_* 키가 None/0이면 보험업 아님 (일반 7점 등급 흐름 유지)."""
    balance_sheet = [{
        "year": 2024,
        "total_assets": 1_000_000_000_000,
        "total_equity": 600_000_000_000,
        "total_liabilities": 400_000_000_000,
        "current_assets": 500_000_000_000,
        "current_liabilities": 200_000_000_000,
        "insurance_liabilities": None,
        "insurance_assets": 0,
    }]
    result = compute_grade_7point(
        metrics={"per": 10.0, "pbr": 1.0, "roe": 10.0},
        balance_sheet=balance_sheet,
        cashflow=[],
        income_stmt=[],
    )
    # 가드 우회 → 일반 7점 등급 산출 (정확한 점수는 미검증, 단 가드 reason 미존재)
    assert "industry_hint" not in result.get("details", {})
    assert result["grade"] in ("A", "B+", "B", "C", "D")


def test_general_manufacturing_unchanged():
    """일반 제조업 BS는 가드 무시 (회귀 0건)."""
    balance_sheet = [{
        "year": 2024,
        "total_assets": 1_000_000_000_000,
        "total_equity": 600_000_000_000,
        "total_liabilities": 400_000_000_000,
        "current_assets": 500_000_000_000,
        "current_liabilities": 200_000_000_000,
        # insurance_* 키 자체 없음 (구버전 BS dict)
    }]
    result = compute_grade_7point(
        metrics={"per": 10.0, "pbr": 1.0, "roe": 12.0},
        balance_sheet=balance_sheet,
        cashflow=[],
        income_stmt=[],
    )
    # 일반 등급 흐름 — schema 호환 + reason 미존재
    assert result["grade"] in ("A", "B+", "B", "C", "D")
    assert "industry_hint" not in result.get("details", {})


def test_empty_balance_sheet_does_not_trigger_guard():
    """빈 BS는 가드 우회 (보험업 단정 금지)."""
    result = compute_grade_7point(
        metrics={"per": 10.0, "pbr": 1.0, "roe": 10.0},
        balance_sheet=[],
        cashflow=[],
        income_stmt=[],
    )
    assert "industry_hint" not in result.get("details", {})


def test_none_balance_sheet_does_not_crash():
    """balance_sheet=None graceful (가드 진입 안 함)."""
    result = compute_grade_7point(
        metrics={"per": 10.0, "pbr": 1.0, "roe": 10.0},
        balance_sheet=None,
        cashflow=[],
        income_stmt=[],
    )
    # 크래시 없이 일반 흐름 진입
    assert "industry_hint" not in result.get("details", {})

"""safety_grade.compute_grade_7point 보험업 진입 가드 회귀 테스트.

2026-05-09 Phase B-1: dart_fin이 추출한 insurance_* BS 필드 존재 시
일반 7점 등급 평가를 건너뛰고 진입 금지(grade=D, valid_entry=False)
+ details.reason으로 보험업 임을 명시.

근거: MarginAnalyst 자문(2026-05-09) — 보험사는 책임준비금이 부채에 포함되어
일반 임계값 적용 시 부채비율 800~1500%로 우량 보험사도 D 양산. Phase B-2는
별도 작업으로 보험사 전용 12점(ROE/자기자본비율/매출성장률/배당안정성) 도입.
"""

from services.safety_grade import compute_grade_7point


def test_insurance_company_returns_d_with_reason():
    """BS에 insurance_liabilities 존재 시 grade=D + reason."""
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
    assert result["grade"] == "D"
    assert result["score"] == 0
    assert result["valid_entry"] is False
    assert result["grade_factor"] == 0.0
    assert "보험업" in result["details"]["reason"]
    assert result["details"]["industry_hint"] == "insurance"


def test_insurance_assets_alone_triggers_guard():
    """insurance_assets만 있어도 보험업 감지 (재보험계약자산 등)."""
    balance_sheet = [{
        "year": 2024,
        "total_assets": 10_000_000_000_000,
        "insurance_assets": 500_000_000_000,
    }]
    result = compute_grade_7point(
        metrics={}, balance_sheet=balance_sheet, cashflow=[], income_stmt=[],
    )
    assert result["grade"] == "D"
    assert result["details"]["industry_hint"] == "insurance"


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

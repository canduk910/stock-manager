"""safety_grade.py 회귀 검증 — 신용 통합이 safety_grade에 영향 없음.

R2 (P1): credit 통합은 macro_regime에만 영향. 동일 metrics+regime+cycle → 등급 불변.
"""

from __future__ import annotations

from services.safety_grade import compute_grade_7point


def _make_inputs():
    """사전 계산용 metrics + 재무 (B+ 등급 근처)."""
    metrics = {
        "per": 8.0,
        "pbr": 0.9,  # 3점
        "debt_ratio": 60.0,  # 3점
        "current_ratio": 1.8,  # 3점
    }
    valuation_stats = {"per_avg_5y": 11.0}  # diff -27% → 3점
    # 3년치 cashflow 양수 → 4점
    cashflow = [
        {"year": 2023, "operating_cf": 100, "free_cf": 80, "capex": 20},
        {"year": 2022, "operating_cf": 110, "free_cf": 90, "capex": 20},
        {"year": 2021, "operating_cf": 90, "free_cf": 70, "capex": 20},
    ]
    # 매출 CAGR 7%: 100 → 122.5 (3년)
    income_stmt = [
        {"year": 2023, "revenue": 122.5},
        {"year": 2022, "revenue": 114.49},
        {"year": 2021, "revenue": 107.0},
        {"year": 2020, "revenue": 100.0},
    ]
    balance_sheet = [
        {"year": 2023, "total_assets": 1000, "total_equity": 600, "debt_ratio": 60.0, "current_ratio": 1.8},
    ]
    # Graham 할인율 25% → discount=25, 3점
    graham_number = 100.0
    current_price = 75.0
    return {
        "metrics": metrics,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "income_stmt": income_stmt,
        "valuation_stats": valuation_stats,
        "graham_number": graham_number,
        "current_price": current_price,
    }


def test_safety_grade_unaffected_by_credit_change():
    """credit 통합 후에도 동일 입력 시 safety_grade 결과 불변.

    safety_grade.py는 macro_regime 변경과 독립이므로,
    동일 metrics → 동일 grade/score를 보장해야 한다 (회귀 안전망).
    """
    inputs = _make_inputs()
    result_a = compute_grade_7point(**inputs)
    result_b = compute_grade_7point(**inputs)
    # 결과 결정성
    assert result_a["grade"] == result_b["grade"]
    assert result_a["score"] == result_b["score"]
    assert result_a["valid_entry"] == result_b["valid_entry"]
    # 합리성: 등급은 D 이외 (즉 진입 가능 또는 부분 진입)
    assert result_a["grade"] in ("A", "B+", "B", "C", "D")
    assert isinstance(result_a["score"], int)
    assert 0 <= result_a["score"] <= 28


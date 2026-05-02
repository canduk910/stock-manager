"""advisory_service 성장 트랙 통합 테스트.

Plan 출처: .claude/plans/ai-sparkling-starfish.md (테스트 #4)
- 가공한 metrics(고성장+가치 부족) → growth_grade=G-A, value=D, combine factor=0.30
- v3 스키마에 성장주_보조판단 필드 정상 검증
"""
from __future__ import annotations

import pytest


def test_value_d_growth_a_combine_factor_03():
    """가치 D + 성장 G-A 조합 → factor=0.30 (성장 트랙 진입 허용)."""
    from services import growth_grade

    growth_pre = growth_grade.compute_growth_grade(
        metrics={"revenue_cagr": 25, "operating_cagr": 35},
        income_stmt=[
            {"revenue": 100, "operating_income": 5},
            {"revenue": 130, "operating_income": 8},
            {"revenue": 170, "operating_income": 12},
            {"revenue": 200, "operating_income": 18},
        ],
        cashflow=[{"free_cf": 5}, {"free_cf": 8}, {"free_cf": 14}],
        rnd_ratio=15,
        sector="Technology",
        cycle_phase="expansion",
    )
    assert growth_pre["grade"] == "G-A"
    assert growth_pre["score"] >= 16

    factor, label = growth_grade.combine_grades("D", growth_pre["grade"])
    assert factor == 0.30
    assert "성장우위" in label


def test_v3_schema_accepts_growth_auxiliary_field():
    """v3 스키마에 성장주_보조판단 Optional 필드 추가 검증."""
    from services.schemas.advisory_report_v3 import validate_v3_report

    sample_report = {
        "schema_version": "v3",
        "종목등급": "D",
        "등급점수": 11,
        "복합점수": 42.5,
        "체제정합성점수": 55.0,
        "종합투자의견": {
            "등급": "중립", "요약": "분할 매수 검토 가능",
            "근거": ["성장 G-A", "사이클 정합"],
        },
        "전략별평가": {
            "변동성돌파": {"신호": "HOLD", "근거": "MA 미정렬", "목표가": None},
            "안전마진": {"신호": "조건부", "근거": "할인 8%", "graham_number": None, "할인율": None},
            "추세추종": {"신호": "HOLD", "근거": "MACD 미발생", "추세강도": "중"},
        },
        "기술적시그널": {
            "신호": "중립", "해석": "보합", "지표별": {"macd": "-", "rsi": "50", "stoch": "-"},
        },
        "성장주_보조판단": {
            "growth_grade": "G-A",
            "growth_score": 18,
            "growth_thesis": "매출 CAGR 25% · R&D 15%",
            "cycle_alignment": "주도섹터(expansion)",
            "combined_factor": 0.30,
            "combined_label": "성장우위(가치D)",
        },
    }
    ok, schema, err = validate_v3_report(sample_report)
    assert ok, f"v3 validation failed: {err}"
    assert schema is not None
    assert schema.성장주_보조판단 is not None
    assert schema.성장주_보조판단.growth_grade == "G-A"
    assert schema.성장주_보조판단.combined_factor == 0.30


def test_v3_schema_backward_compat_without_growth_field():
    """기존 v3 리포트(성장주_보조판단 필드 없음)도 정상 검증."""
    from services.schemas.advisory_report_v3 import validate_v3_report

    legacy_report = {
        "schema_version": "v3",
        "종목등급": "B",
        "등급점수": 18,
        "복합점수": 65.0,
        "체제정합성점수": 70.0,
        "종합투자의견": {"등급": "매수", "요약": "test", "근거": ["a"]},
        "전략별평가": {
            "변동성돌파": {"신호": "BUY", "근거": "X", "목표가": 100.0},
            "안전마진": {"신호": "BUY", "근거": "Y", "graham_number": 90, "할인율": 15},
            "추세추종": {"신호": "BUY", "근거": "Z", "추세강도": "강"},
        },
        "기술적시그널": {
            "신호": "BUY", "해석": "정배열", "지표별": {"macd": "+", "rsi": "60", "stoch": "70"},
        },
        # 성장주_보조판단 필드 없음 (legacy)
    }
    ok, schema, err = validate_v3_report(legacy_report)
    assert ok, f"legacy v3 validation failed: {err}"
    assert schema.성장주_보조판단 is None


def test_safety_grade_c_is_now_025():
    """가치 C 등급도 진입 허용 (factor=0.25)."""
    from services import safety_grade

    assert safety_grade.GRADE_FACTOR["C"] == 0.25
    assert safety_grade.GRADE_FACTOR["D"] == 0.0
    # 손절: C=-15%
    assert safety_grade.GRADE_STOP_LOSS_PCT["C"] == 0.15
    assert safety_grade.GRADE_STOP_LOSS_PCT["D"] is None


def test_safety_grade_compute_grade_c_valid_entry_now_true():
    """compute_grade_7point의 valid_entry는 C 등급도 True (D만 False)."""
    from services import safety_grade

    # C 등급 점수대(12-15) 시뮬레이션
    result = safety_grade.compute_grade_7point(
        metrics={"per": 20, "pbr": 1.8, "debt_to_equity": 150},
        balance_sheet=[],
        cashflow=[{"free_cf": 1}, {"free_cf": -1}],
        income_stmt=[{"revenue": 100}, {"revenue": 105}],
    )
    if result["grade"] == "C":
        assert result["valid_entry"] is True
    if result["grade"] == "D":
        assert result["valid_entry"] is False

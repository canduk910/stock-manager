"""성장주 보조 등급 모듈 단위 테스트.

Plan 출처: .claude/plans/ai-sparkling-starfish.md (테스트 #1)
"""
from __future__ import annotations

import pytest

from services import growth_grade


# ── compute_growth_grade ─────────────────────────────────────────────────


def test_compute_growth_grade_g_a_high_growth_tech():
    """가치 평가에 불리한 고성장 기술주: G-A 등급."""
    g = growth_grade.compute_growth_grade(
        metrics={"revenue_cagr": 25, "operating_cagr": 30},
        income_stmt=[
            {"revenue": 100, "operating_income": 10},
            {"revenue": 130, "operating_income": 15},
            {"revenue": 170, "operating_income": 22},
            {"revenue": 200, "operating_income": 28},
        ],
        cashflow=[{"free_cf": 5}, {"free_cf": 8}, {"free_cf": 12}],
        rnd_ratio=12,
        sector="Technology",
        cycle_phase="expansion",
    )
    assert g["grade"] == "G-A"
    assert g["score"] >= 16
    # 5지표 모두 채점 결과 존재
    assert g["details"]["revenue_cagr"]["points"] == 4
    assert g["details"]["operating_cagr"]["points"] == 4
    assert g["details"]["fcf_trend"]["points"] == 4
    assert g["details"]["rnd_ratio"]["points"] == 3
    assert g["details"]["cycle_alignment"]["points"] == 4


def test_compute_growth_grade_g_b_mid_range():
    """중간 성장 종목: G-B."""
    g = growth_grade.compute_growth_grade(
        metrics={"revenue_cagr": 8, "operating_cagr": 6},
        income_stmt=[],
        cashflow=[{"free_cf": 5}, {"free_cf": 4}, {"free_cf": 6}],
        rnd_ratio=5,
        sector="Industrials",
        cycle_phase="recovery",
    )
    assert g["grade"] == "G-B"
    assert 12 <= g["score"] < 16


def test_compute_growth_grade_g_c_low_growth():
    """저성장+FCF 음수 종목: G-C."""
    g = growth_grade.compute_growth_grade(
        metrics={"revenue_cagr": 1, "operating_cagr": -2},
        income_stmt=[],
        cashflow=[{"free_cf": -5}, {"free_cf": -3}, {"free_cf": -1}],
        rnd_ratio=1,
        sector="Utilities",
        cycle_phase="expansion",  # 반대 사이클
    )
    assert g["grade"] == "G-C"
    assert g["score"] < 12


def test_compute_growth_grade_missing_data_defaults():
    """데이터 부족 시 안전 기본값 — 점수 1~2 위주, G-C 등급."""
    g = growth_grade.compute_growth_grade(
        metrics=None,
        income_stmt=None,
        cashflow=None,
        rnd_ratio=None,
        sector=None,
        cycle_phase=None,
    )
    assert g["grade"] in ("G-B", "G-C")  # 모두 1~2점이면 G-C 또는 G-B 경계
    assert g["score"] >= 0


def test_compute_growth_grade_cycle_alignment_opposite():
    """반대 사이클 섹터는 정합성 1점."""
    g = growth_grade.compute_growth_grade(
        metrics={"revenue_cagr": 12, "operating_cagr": 15},
        income_stmt=[],
        cashflow=[{"free_cf": 10}, {"free_cf": 12}, {"free_cf": 15}],
        rnd_ratio=2,
        sector="Utilities",  # contraction 주도
        cycle_phase="expansion",
    )
    # Utilities는 contraction 주도 섹터 → expansion 사이클에서 반대 사이클
    assert g["details"]["cycle_alignment"]["points"] == 1
    assert "반대사이클" in g["details"]["cycle_alignment"]["label"]


def test_compute_growth_grade_cycle_alignment_match():
    """주도 섹터 직접 매칭은 4점."""
    g = growth_grade.compute_growth_grade(
        metrics={"revenue_cagr": 10},
        income_stmt=[],
        cashflow=[],
        rnd_ratio=None,
        sector="기술",
        cycle_phase="expansion",
    )
    assert g["details"]["cycle_alignment"]["points"] == 4


# ── combine_grades ──────────────────────────────────────────────────────


def test_combine_grades_value_a_takes_precedence():
    """가치 A는 성장과 무관하게 factor=1.0."""
    factor, label = growth_grade.combine_grades("A", "G-C")
    assert factor == 1.0
    assert label == "가치우위"


def test_combine_grades_value_b_growth_a_label_mix():
    """가치 B + 성장 G-A → factor=0.5(가치 우선) + '가치+성장혼합' 라벨."""
    factor, label = growth_grade.combine_grades("B", "G-A")
    assert factor == 0.5
    assert label == "가치+성장혼합"


def test_combine_grades_value_c_factor_025():
    """가치 C 등급 → factor=0.25 (safety_grade.GRADE_FACTOR['C'])."""
    factor, label = growth_grade.combine_grades("C", "G-B")
    assert factor == 0.25
    assert "가치C" in label


def test_combine_grades_value_d_growth_a_grants_entry():
    """가치 D + 성장 G-A → factor=0.30 (성장 트랙 진입 허용)."""
    factor, label = growth_grade.combine_grades("D", "G-A")
    assert factor == 0.30
    assert label == "성장우위(가치D)"


def test_combine_grades_value_d_growth_b_blocks_entry():
    """가치 D + 성장 G-B/G-C → factor=0 (진입 금지)."""
    factor_b, label_b = growth_grade.combine_grades("D", "G-B")
    assert factor_b == 0.0
    assert label_b == "진입금지"

    factor_c, label_c = growth_grade.combine_grades("D", "G-C")
    assert factor_c == 0.0
    assert label_c == "진입금지"

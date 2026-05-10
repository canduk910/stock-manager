"""REQ-DOMAIN-002: composite_score sector 비의존성 회귀 가드.

MarginAnalyst: 안전마진/등급 산출은 7지표 정량 기반.
sector 문자열은 composite_score에 0% 영향.
"""
from __future__ import annotations

import pytest


def _make_metrics(sector_value):
    """7지표 + sector 변동만 다른 metrics dict."""
    return {
        "per": 12.0,
        "pbr": 1.2,
        "roe": 0.15,
        "debt_ratio": 0.5,
        "interest_coverage": 8.0,
        "fcf": 1000,
        "dividend_yield": 0.025,
        "sector": sector_value,
    }


def test_composite_score_independent_of_sector():
    """ValueScreener 복합점수는 sector 키 변동에 영향 받지 않는다."""
    from services.safety_grade import compute_composite_score

    s1 = compute_composite_score(_make_metrics("반도체"))
    s2 = compute_composite_score(_make_metrics("Technology"))
    s3 = compute_composite_score(_make_metrics(None))
    s4 = compute_composite_score(_make_metrics(""))
    s5 = compute_composite_score(_make_metrics("기타"))

    # composite_score는 sector 변경에 0% 변동
    assert s1 == s2 == s3 == s4 == s5
    assert s1 is not None and s1 > 0


def test_grade_7point_independent_of_sector():
    """A/B+/B/C/D 7점 등급도 sector에 독립."""
    from services.safety_grade import compute_grade_7point

    base_args = dict(
        balance_sheet=[{"year": 2024, "debt_ratio": 50, "current_ratio": 200}],
        cashflow=[{"year": 2022, "free_cf": 100},
                  {"year": 2023, "free_cf": 120},
                  {"year": 2024, "free_cf": 150}],
        income_stmt=[{"year": 2020, "revenue": 800},
                     {"year": 2021, "revenue": 900},
                     {"year": 2022, "revenue": 1000},
                     {"year": 2023, "revenue": 1100},
                     {"year": 2024, "revenue": 1200}],
        valuation_stats=None,
        graham_number=None,
        current_price=None,
    )

    g1 = compute_grade_7point(_make_metrics("반도체"), **base_args)
    g2 = compute_grade_7point(_make_metrics("Technology"), **base_args)
    g3 = compute_grade_7point(_make_metrics(None), **base_args)

    assert g1.get("grade") == g2.get("grade") == g3.get("grade")
    assert g1.get("score") == g2.get("score") == g3.get("score")

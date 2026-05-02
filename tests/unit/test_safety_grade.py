"""services/safety_grade.py 7점 등급/복합점수/포지션 사이징 단위 테스트."""

import pytest

from services.safety_grade import (
    GRADE_FACTOR,
    GRADE_STOP_LOSS_PCT,
    _score_discount,
    _score_per_vs_avg,
    _score_pbr,
    _score_debt_ratio,
    _score_current_ratio,
    _score_fcf_trend,
    _score_revenue_cagr,
    _calc_discount,
    _count_fcf_years_positive,
    _calc_revenue_cagr,
    compute_grade_7point,
    compute_composite_score,
    compute_regime_alignment,
    compute_position_size,
    compute_stop_loss,
    compute_risk_reward,
)


# ── _score_discount ───────────────────────────────────────────

class TestScoreDiscount:
    def test_4pt(self):
        assert _score_discount(45.0) == 4

    def test_3pt(self):
        assert _score_discount(30.0) == 3

    def test_2pt(self):
        assert _score_discount(10.0) == 2

    def test_1pt_negative(self):
        assert _score_discount(-5.0) == 1

    def test_none(self):
        assert _score_discount(None) == 1

    def test_boundary_40(self):
        # 정확히 40은 >40이 아니므로 3점
        assert _score_discount(40.0) == 3

    def test_boundary_20(self):
        assert _score_discount(20.0) == 2

    def test_boundary_0(self):
        assert _score_discount(0.0) == 1

    def test_boundary_40_01(self):
        assert _score_discount(40.01) == 4

    def test_boundary_20_01(self):
        assert _score_discount(20.01) == 3


# ── _score_per_vs_avg ─────────────────────────────────────────

class TestScorePerVsAvg:
    def test_4pt(self):
        # PER=5, avg=10 -> diff=-50%
        assert _score_per_vs_avg(5, 10) == 4

    def test_3pt(self):
        # PER=8, avg=10 -> diff=-20%
        assert _score_per_vs_avg(8, 10) == 3

    def test_2pt(self):
        # PER=10, avg=10 -> diff=0%
        assert _score_per_vs_avg(10, 10) == 2

    def test_1pt(self):
        # PER=15, avg=10 -> diff=+50%
        assert _score_per_vs_avg(15, 10) == 1

    def test_none_per(self):
        assert _score_per_vs_avg(None, 10) == 2

    def test_none_avg(self):
        assert _score_per_vs_avg(10, None) == 2

    def test_zero_avg(self):
        assert _score_per_vs_avg(10, 0) == 2

    def test_negative_avg(self):
        assert _score_per_vs_avg(10, -5) == 2

    def test_boundary_minus_30(self):
        # diff = (7-10)/10*100 = -30% exactly -> <-30 is False -> 3점
        assert _score_per_vs_avg(7, 10) == 3

    def test_boundary_minus_10(self):
        # diff = (9-10)/10*100 = -10% exactly -> <-10 is False -> 2점
        assert _score_per_vs_avg(9, 10) == 2


# ── _score_pbr ────────────────────────────────────────────────

class TestScorePbr:
    def test_4pt(self):
        assert _score_pbr(0.5) == 4

    def test_3pt(self):
        assert _score_pbr(0.8) == 3

    def test_2pt(self):
        assert _score_pbr(1.2) == 2

    def test_1pt(self):
        assert _score_pbr(2.0) == 1

    def test_none(self):
        assert _score_pbr(None) == 2

    def test_boundary_07(self):
        # 정확히 0.7은 <0.7이 아니므로 3점
        assert _score_pbr(0.7) == 3

    def test_boundary_10(self):
        assert _score_pbr(1.0) == 2

    def test_boundary_15(self):
        assert _score_pbr(1.5) == 1


# ── _score_debt_ratio ─────────────────────────────────────────

class TestScoreDebtRatio:
    def test_4pt(self):
        assert _score_debt_ratio(30) == 4

    def test_3pt(self):
        assert _score_debt_ratio(70) == 3

    def test_2pt(self):
        assert _score_debt_ratio(150) == 2

    def test_1pt(self):
        assert _score_debt_ratio(300) == 1

    def test_none(self):
        assert _score_debt_ratio(None) == 2

    def test_boundary_50(self):
        assert _score_debt_ratio(50) == 3

    def test_boundary_100(self):
        assert _score_debt_ratio(100) == 2

    def test_boundary_200(self):
        assert _score_debt_ratio(200) == 1


# ── _score_current_ratio ──────────────────────────────────────

class TestScoreCurrentRatio:
    def test_percent_input(self):
        # 150 > 10 -> /100 = 1.5 -> 1.5는 >1.5가 아님 -> >1.0 -> 2점
        assert _score_current_ratio(150) == 2

    def test_decimal_input(self):
        # 1.5 <= 10 -> 배수 그대로 -> 1.0~1.5 -> 2점 (> 1.0, not > 1.5)
        assert _score_current_ratio(1.5) == 2

    def test_high(self):
        assert _score_current_ratio(2.5) == 4

    def test_low(self):
        assert _score_current_ratio(0.8) == 1

    def test_none(self):
        assert _score_current_ratio(None) == 2

    def test_boundary_10_is_decimal(self):
        # 정확히 10은 >10이 아니므로 배수로 간주 -> 10 > 2.0 -> 4점
        assert _score_current_ratio(10) == 4

    def test_percent_200(self):
        # 200 > 10 -> /100 = 2.0 -> not > 2.0 -> 1.5-2.0 -> 3점
        assert _score_current_ratio(200) == 3

    def test_percent_250(self):
        # 250 > 10 -> /100 = 2.5 -> > 2.0 -> 4점
        assert _score_current_ratio(250) == 4


# ── _score_fcf_trend ──────────────────────────────────────────

class TestScoreFcfTrend:
    def test_3years(self):
        assert _score_fcf_trend(3) == 4

    def test_2years(self):
        assert _score_fcf_trend(2) == 3

    def test_1year(self):
        assert _score_fcf_trend(1) == 2

    def test_0years(self):
        assert _score_fcf_trend(0) == 1

    def test_more_than_3(self):
        assert _score_fcf_trend(5) == 4


# ── _score_revenue_cagr ──────────────────────────────────────

class TestScoreRevenueCagr:
    def test_4pt(self):
        assert _score_revenue_cagr(15) == 4

    def test_3pt(self):
        assert _score_revenue_cagr(7) == 3

    def test_2pt(self):
        assert _score_revenue_cagr(3) == 2

    def test_1pt(self):
        assert _score_revenue_cagr(-5) == 1

    def test_none(self):
        assert _score_revenue_cagr(None) == 2

    def test_boundary_10(self):
        assert _score_revenue_cagr(10) == 3  # >10이어야 4

    def test_boundary_5(self):
        assert _score_revenue_cagr(5) == 2  # >5이어야 3

    def test_boundary_0(self):
        assert _score_revenue_cagr(0) == 1  # >0이어야 2


# ── _calc_discount ────────────────────────────────────────────

class TestCalcDiscount:
    def test_basic(self):
        # (75000 - 50000) / 50000 * 100 = 50%
        assert _calc_discount(75000, 50000) == pytest.approx(50.0)

    def test_premium(self):
        # (40000 - 50000) / 50000 * 100 = -20%
        assert _calc_discount(40000, 50000) == pytest.approx(-20.0)

    def test_none_graham(self):
        assert _calc_discount(None, 50000) is None

    def test_none_price(self):
        assert _calc_discount(75000, None) is None

    def test_zero_price(self):
        assert _calc_discount(75000, 0) is None


# ── _count_fcf_years_positive ─────────────────────────────────

class TestCountFcfYearsPositive:
    def test_3years_consecutive(self):
        cf = [
            {"operating_cf": 100, "capex": 30},
            {"operating_cf": 120, "capex": 40},
            {"operating_cf": 150, "capex": 50},
        ]
        assert _count_fcf_years_positive(cf) == 3

    def test_break_in_middle(self):
        cf = [
            {"operating_cf": 100, "capex": 30},
            {"operating_cf": 20, "capex": 50},  # FCF = -30
            {"operating_cf": 200, "capex": 50},
        ]
        # 역순: [양, 음, 양] -> 양(1) -> 음 break -> 결과 1
        assert _count_fcf_years_positive(cf) == 1

    def test_empty(self):
        assert _count_fcf_years_positive([]) == 0

    def test_with_direct_fcf(self):
        cf = [{"fcf": 100}]
        assert _count_fcf_years_positive(cf) == 1

    def test_with_free_cf_key(self):
        cf = [{"free_cf": 200}]
        assert _count_fcf_years_positive(cf) == 1

    def test_op_cf_minus_capex(self):
        cf = [{"operating_cf": 100, "capex": 30}]  # FCF = 70
        assert _count_fcf_years_positive(cf) == 1

    def test_negative_fcf(self):
        cf = [{"operating_cf": 10, "capex": 50}]  # FCF = -40
        assert _count_fcf_years_positive(cf) == 0

    def test_only_last_3_considered(self):
        cf = [
            {"fcf": -100},  # 4년 전 (무시됨)
            {"fcf": 100},
            {"fcf": 200},
            {"fcf": 300},
        ]
        assert _count_fcf_years_positive(cf) == 3


# ── _calc_revenue_cagr ───────────────────────────────────────

class TestCalcRevenueCagr:
    def test_positive_growth(self):
        income = [{"revenue": 100_000_000}, {"revenue": 133_100_000}]
        result = _calc_revenue_cagr(income)
        assert result == pytest.approx(33.1, abs=0.1)

    def test_negative_growth(self):
        income = [{"revenue": 100_000_000}, {"revenue": 80_000_000}]
        result = _calc_revenue_cagr(income)
        assert result == pytest.approx(-20.0, abs=0.1)

    def test_zero_first_revenue(self):
        income = [{"revenue": 0}, {"revenue": 100_000_000}]
        assert _calc_revenue_cagr(income) is None

    def test_single_year(self):
        income = [{"revenue": 100}]
        assert _calc_revenue_cagr(income) is None

    def test_empty(self):
        assert _calc_revenue_cagr([]) is None

    def test_3year_cagr(self):
        # CAGR = (160/100)^(1/3) - 1 = 0.1696 -> 16.96% -> ~17.0
        income = [
            {"revenue": 100}, {"revenue": 120}, {"revenue": 140}, {"revenue": 160},
        ]
        result = _calc_revenue_cagr(income)
        expected = ((160 / 100) ** (1 / 3) - 1) * 100
        assert result == pytest.approx(expected, abs=0.1)

    def test_none_revenue(self):
        income = [{"revenue": None}, {"revenue": 100}]
        assert _calc_revenue_cagr(income) is None


# ── compute_grade_7point (통합) ───────────────────────────────

def _make_perfect_inputs():
    """28점 만점 입력."""
    metrics = {"per": 5, "pbr": 0.5, "roe": 20}
    bs = [{"debt_ratio": 30, "current_ratio": 2.5}]
    cf = [{"fcf": 100}, {"fcf": 200}, {"fcf": 300}]
    income = [{"revenue": 100}, {"revenue": 120}, {"revenue": 140}, {"revenue": 180}]
    vs = {"per_avg_5y": 15}
    return metrics, bs, cf, income, vs


class TestComputeGrade7Point:
    def test_grade_A_perfect(self):
        metrics, bs, cf, income, vs = _make_perfect_inputs()
        result = compute_grade_7point(metrics, bs, cf, income, vs,
                                       graham_number=100000, current_price=50000)
        assert result["grade"] == "A"
        assert result["score"] >= 24
        assert result["valid_entry"] is True
        assert result["grade_factor"] == 1.0

    def test_grade_A_boundary_24(self):
        # 최소 A: 24점. 7항목 중 일부를 3점으로 낮춰서 24점 맞춤
        metrics = {"per": 10, "pbr": 0.8}  # pbr=3
        bs = [{"debt_ratio": 70, "current_ratio": 1.8}]  # debt=3, current=3
        cf = [{"fcf": 100}, {"fcf": 200}, {"fcf": 300}]  # 4
        income = [{"revenue": 100}, {"revenue": 120}, {"revenue": 140}, {"revenue": 180}]  # 4: ~21.6%
        vs = {"per_avg_5y": 15}  # per=10 vs avg=15 -> (10-15)/15*100=-33.3% -> 4
        result = compute_grade_7point(metrics, bs, cf, income, vs,
                                       graham_number=100000, current_price=50000)  # discount=100% -> 4
        assert result["score"] >= 24
        assert result["grade"] == "A"

    def test_grade_C_not_valid(self):
        metrics = {"per": 20, "pbr": 2.0}
        bs = [{"debt_ratio": 250}]
        cf = [{"fcf": -100}]
        income = [{"revenue": 100}, {"revenue": 80}]
        result = compute_grade_7point(metrics, bs, cf, income)
        assert result["grade"] in ("C", "D")
        assert result["valid_entry"] is False

    def test_grade_D(self):
        metrics = {}
        result = compute_grade_7point(metrics, [], [], [])
        # 모든 None -> 각 1~2점, 합계 낮음
        assert result["grade"] in ("C", "D")

    def test_all_none_metrics(self):
        result = compute_grade_7point({}, [], [], [])
        assert "score" in result
        assert "grade" in result
        assert "details" in result

    def test_details_structure(self):
        metrics, bs, cf, income, vs = _make_perfect_inputs()
        result = compute_grade_7point(metrics, bs, cf, income, vs,
                                       graham_number=100000, current_price=50000)
        details = result["details"]
        expected_keys = {"discount", "per_vs_avg", "pbr", "debt_ratio",
                         "current_ratio", "fcf_trend", "revenue_cagr"}
        assert set(details.keys()) == expected_keys
        for key in expected_keys:
            assert "points" in details[key]

    def test_grade_factor_mapping(self):
        # 2026-05-01: C 등급은 0 → 0.25 (성장 트랙 도입과 함께 부분 진입 허용)
        # D는 여전히 0 (가치 평가 진입 금지). 성장 G-A 시 growth_grade.combine_grades에서 0.30 부여.
        assert GRADE_FACTOR["A"] == 1.0
        assert GRADE_FACTOR["B+"] == 0.75
        assert GRADE_FACTOR["B"] == 0.5
        assert GRADE_FACTOR["C"] == 0.25
        assert GRADE_FACTOR["D"] == 0.0

    def test_grade_cutoffs(self):
        # 직접 점수별 등급 검증
        metrics, bs, cf, income, vs = _make_perfect_inputs()
        result = compute_grade_7point(metrics, bs, cf, income, vs,
                                       graham_number=100000, current_price=50000)
        score = result["score"]
        grade = result["grade"]
        if score >= 24:
            assert grade == "A"
        elif score >= 20:
            assert grade == "B+"
        elif score >= 16:
            assert grade == "B"
        elif score >= 12:
            assert grade == "C"
        else:
            assert grade == "D"


# ── compute_composite_score ───────────────────────────────────

class TestComputeCompositeScore:
    def test_basic(self):
        metrics = {"per": 10, "pbr": 1.0, "roe": 15, "dividend_yield": 3.5}
        result = compute_composite_score(metrics)
        # (1/10*0.3 + 1/1.0*0.3 + 15/100*0.25 + 3.5/100*0.15) * 100
        expected = (0.1 * 0.3 + 1.0 * 0.3 + 0.15 * 0.25 + 0.035 * 0.15) * 100
        assert result == pytest.approx(expected, abs=0.1)

    def test_none_metrics(self):
        assert compute_composite_score(None) is None

    def test_empty_dict(self):
        # 빈 dict는 falsy -> `not metrics` = True -> None 반환
        result = compute_composite_score({})
        assert result is None

    def test_negative_per(self):
        metrics = {"per": -5, "pbr": 1.0, "roe": 10}
        result = compute_composite_score(metrics)
        # PER 음수 -> per_inv = 0
        expected = (0 * 0.3 + 1.0 * 0.3 + 0.10 * 0.25 + 0) * 100
        assert result == pytest.approx(expected, abs=0.1)

    def test_zero_per(self):
        metrics = {"per": 0, "pbr": 1.0}
        result = compute_composite_score(metrics)
        assert result is not None
        assert result >= 0

    def test_max_clamp(self):
        # 극단적으로 높은 점수 -> 100 클램핑
        metrics = {"per": 0.5, "pbr": 0.1, "roe": 80, "dividend_yield": 20}
        result = compute_composite_score(metrics)
        assert result <= 100.0

    def test_min_clamp(self):
        metrics = {"per": -1, "pbr": -1, "roe": -50, "dividend_yield": -10}
        result = compute_composite_score(metrics)
        assert result >= 0.0

    def test_dy_percent_form(self):
        # DY=3.5 (>1이면 %) -> /100 = 0.035
        metrics = {"dividend_yield": 3.5}
        result = compute_composite_score(metrics)
        expected = (0 + 0 + 0 + 0.035 * 0.15) * 100
        assert result == pytest.approx(expected, abs=0.1)

    def test_dy_decimal_form(self):
        # DY=0.035 (<1이면 소수점) -> 그대로 사용
        metrics = {"dividend_yield": 0.035}
        result = compute_composite_score(metrics)
        expected = (0 + 0 + 0 + 0.035 * 0.15) * 100
        assert result == pytest.approx(expected, abs=0.1)


# ── compute_regime_alignment ──────────────────────────────────

class TestComputeRegimeAlignment:
    def test_perfect_alignment(self):
        result = compute_regime_alignment("accumulation", 28, 3, 75)
        assert result == pytest.approx(100.0)

    def test_grade_below_expected(self):
        result = compute_regime_alignment("selective", 12, 3, 65)
        assert result < 100.0

    def test_no_stock_pct(self):
        # stock_pct None -> 2항목(등급+FCF) 50/50 가중
        result = compute_regime_alignment("selective", 20, 3)
        # grade_align=100(20>=20), fcf_align=100(3년) -> 100
        assert result == pytest.approx(100.0)

    def test_none_grade(self):
        result = compute_regime_alignment("selective", None, 3)
        # grade_align=50(기본), fcf_align=100 -> (50*0.5 + 100*0.5)=75
        assert result == pytest.approx(75.0)

    def test_defensive_regime(self):
        result = compute_regime_alignment("defensive", 20, 3, 25)
        # expected_score=28, grade_score=20 -> diff=-8 -> grade_align = max(0, 100-8*100/12) = 33.3
        # fcf_align=100, stock_align=100(|25-25|<=5)
        # = 33.3*0.4 + 100*0.3 + 100*0.3 = 13.3 + 30 + 30 = 73.3
        assert result == pytest.approx(73.3, abs=0.1)

    def test_stock_pct_exact_match(self):
        result = compute_regime_alignment("accumulation", 28, 3, 75)
        assert result == pytest.approx(100.0)

    def test_stock_pct_within_5(self):
        result = compute_regime_alignment("accumulation", 28, 3, 72)
        # |72-75|=3 <= 5 -> stock_align=100
        assert result == pytest.approx(100.0)

    def test_stock_pct_far(self):
        result = compute_regime_alignment("accumulation", 28, 3, 50)
        # |50-75|=25 >= 20 -> stock_align=0
        expected = 100 * 0.4 + 100 * 0.3 + 0 * 0.3
        assert result == pytest.approx(expected, abs=0.1)

    def test_fcf_0_years(self):
        result = compute_regime_alignment("accumulation", 28, 0)
        # grade_align=100, fcf_align=25 -> (100*0.5 + 25*0.5) = 62.5
        assert result == pytest.approx(62.5)

    def test_fcf_none(self):
        result = compute_regime_alignment("accumulation", 28, None)
        # fcf_align=50 -> (100*0.5 + 50*0.5) = 75
        assert result == pytest.approx(75.0)


# ── compute_position_size ─────────────────────────────────────

class TestComputePositionSize:
    def test_A_accumulation(self):
        result = compute_position_size("A", 5, 100_000_000, 50_000_000, 50_000)
        # target_pct = 5 * 1.0 / 100 = 0.05
        # max_amount = 100M * 0.05 = 5M
        # available = min(5M, 50M) = 5M
        # qty = 5M // 50000 = 100
        assert result["qty"] == 100
        assert result["recommendation"] == "ENTER"
        assert result["position_pct"] == pytest.approx(5.0)

    def test_Bplus_selective(self):
        result = compute_position_size("B+", 4, 100_000_000, 50_000_000, 50_000)
        # target_pct = 4 * 0.75 / 100 = 0.03
        # max_amount = 100M * 0.03 = 3M
        # qty = 3M // 50000 = 60
        assert result["qty"] == 60
        assert result["recommendation"] == "ENTER"
        assert result["position_pct"] == pytest.approx(3.0)

    def test_C_partial_entry(self):
        # 2026-05-01: C 등급 factor=0.25 → 부분 진입 허용
        # target_pct = 4 * 0.25 / 100 = 0.01, max_amount = 100M * 0.01 = 1M
        # qty = 1M // 50000 = 20
        result = compute_position_size("C", 4, 100_000_000, 50_000_000, 50_000)
        assert result["qty"] == 20
        assert result["recommendation"] == "ENTER"
        assert result["grade_factor"] == 0.25

    def test_D_skip(self):
        # D 등급은 여전히 진입 금지 (가치 평가 기준). 성장 트랙은 별도 모듈에서 처리.
        result = compute_position_size("D", 4, 100_000_000, 50_000_000, 50_000)
        assert result["qty"] == 0
        assert result["recommendation"] == "SKIP"

    def test_cash_limited(self):
        result = compute_position_size("A", 5, 100_000_000, 1_000_000, 50_000)
        # max_amount=5M, available=min(5M, 1M)=1M, qty=1M//50000=20
        assert result["qty"] == 20
        assert result["recommendation"] == "ENTER"

    def test_zero_price(self):
        result = compute_position_size("A", 5, 100_000_000, 50_000_000, 0)
        assert result["qty"] == 0
        assert result["recommendation"] == "SKIP"

    def test_negative_price(self):
        result = compute_position_size("A", 5, 100_000_000, 50_000_000, -100)
        assert result["qty"] == 0
        assert result["recommendation"] == "SKIP"

    def test_hold_no_cash(self):
        result = compute_position_size("A", 5, 100_000_000, 0, 50_000)
        assert result["qty"] == 0
        assert result["recommendation"] == "HOLD"

    def test_B_grade(self):
        result = compute_position_size("B", 4, 100_000_000, 50_000_000, 50_000)
        # factor=0.5, target_pct=4*0.5/100=0.02, max=2M, qty=40
        assert result["qty"] == 40
        assert result["grade_factor"] == 0.5


# ── compute_stop_loss ─────────────────────────────────────────

class TestComputeStopLoss:
    def test_A_grade(self):
        # -8%
        assert compute_stop_loss("A", 50000) == pytest.approx(46000.0)

    def test_Bplus_grade(self):
        # -10%
        assert compute_stop_loss("B+", 50000) == pytest.approx(45000.0)

    def test_B_grade(self):
        # -12%
        assert compute_stop_loss("B", 50000) == pytest.approx(44000.0)

    def test_C_grade(self):
        # 2026-05-01: C 등급 손절 -15% (부분 진입 허용에 따른 신규 정책)
        assert compute_stop_loss("C", 50000) == pytest.approx(42500.0)

    def test_D_grade(self):
        # D는 여전히 진입 금지 → 손절 None
        assert compute_stop_loss("D", 50000) is None

    def test_zero_price(self):
        assert compute_stop_loss("A", 0) is None

    def test_negative_price(self):
        assert compute_stop_loss("A", -100) is None


# ── compute_risk_reward ───────────────────────────────────────

class TestComputeRiskReward:
    def test_basic(self):
        # risk=50000-46000=4000, reward=60000-50000=10000, rr=2.5
        assert compute_risk_reward(50000, 46000, 60000) == pytest.approx(2.5)

    def test_below_2(self):
        # risk=4000, reward=5000-50000=-45000? 아닌, 보류 예시
        # entry=50000, stop=46000, target=55000 -> risk=4000, reward=5000 -> rr=1.25
        assert compute_risk_reward(50000, 46000, 55000) == pytest.approx(1.25)

    def test_none_inputs(self):
        assert compute_risk_reward(None, None, None) is None
        assert compute_risk_reward(50000, None, 60000) is None
        assert compute_risk_reward(None, 46000, 60000) is None

    def test_stop_above_entry(self):
        assert compute_risk_reward(50000, 55000, 60000) is None

    def test_stop_equals_entry(self):
        assert compute_risk_reward(50000, 50000, 60000) is None

    def test_negative_reward(self):
        # target < entry -> reward < 0 -> rr < 0
        result = compute_risk_reward(50000, 46000, 45000)
        assert result == pytest.approx(-1.25)

    def test_zero_entry(self):
        assert compute_risk_reward(0, -1, 10) is None

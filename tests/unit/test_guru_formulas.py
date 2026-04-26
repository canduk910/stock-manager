"""구루 공식 단위 테스트 — 6개 공식 + 패널 + Value Trap."""

import pytest
from services.guru_formulas import (
    calc_greenblatt,
    calc_neff,
    calc_seo_expected_return,
    calc_graham_ncav,
    calc_fisher_psr,
    calc_piotroski_fscore,
    calc_guru_panel,
    check_value_trap,
    REGIME_GURU_PARAMS,
)


# ── Greenblatt Magic Formula ─────────────────────────────────────

class TestGreenblatt:
    def test_normal_case(self):
        r = calc_greenblatt(
            operating_income=500_000_000,      # 5억
            current_assets=3_000_000_000,      # 30억
            current_liabilities=1_000_000_000, # 10억
            ppe=1_000_000_000,                 # 10억
            mktcap=10_000_000_000,             # 100억
            total_liabilities=2_000_000_000,   # 20억
            cash_and_equiv=500_000_000,        # 5억
        )
        assert r["calculable"] is True
        # ROIC = 5억 / (20억 + 10억) = 16.67%
        assert r["roic"] == pytest.approx(16.67, abs=0.01)
        assert r["roic_score"] == 3  # >15%
        # EV = 100억 + 20억 - 5억 = 115억
        # EY = 5억 / 115억 = 4.35%
        assert r["earnings_yield"] == pytest.approx(4.35, abs=0.01)
        assert r["ey_score"] == 1  # <5%
        assert r["total_score"] == 4  # 3+1

    def test_high_roic_high_ey(self):
        r = calc_greenblatt(
            operating_income=1_000_000_000,
            current_assets=2_000_000_000,
            current_liabilities=500_000_000,
            ppe=500_000_000,
            mktcap=3_000_000_000,
            total_liabilities=500_000_000,
            cash_and_equiv=100_000_000,
        )
        assert r["calculable"] is True
        # ROIC = 10억 / (15억 + 5억) = 50%
        assert r["roic_score"] == 4  # >25%
        # EV = 30억 + 5억 - 1억 = 34억, EY = 10억/34억 = 29.4%
        assert r["ey_score"] == 4  # >15%
        assert r["total_score"] == 8

    def test_missing_operating_income(self):
        r = calc_greenblatt(None, 100, 50, 50, 1000, 200, 100)
        assert r["calculable"] is False
        assert r["total_score"] == 2

    def test_zero_mktcap(self):
        r = calc_greenblatt(100, 200, 100, 100, 0, 50, 10)
        assert r["calculable"] is False

    def test_zero_invested_capital(self):
        # 유동자산=유동부채, PPE=0 → invested_capital=0 → ROIC=None
        r = calc_greenblatt(100_000, 500, 500, 0, 1_000_000, 200, 100)
        assert r["roic"] is None
        # EY는 계산 가능
        assert r["earnings_yield"] is not None
        assert r["calculable"] is True


# ── Neff Total Return Ratio ──────────────────────────────────────

class TestNeff:
    def test_normal_case(self):
        # EPS: 1000→1200→1440→1728 (20% CAGR)
        r = calc_neff([1000, 1200, 1440, 1728], dividend_yield=3.0, per=10.0)
        assert r["calculable"] is True
        assert r["eps_cagr"] == pytest.approx(20.0, abs=0.5)
        # Neff = (20 + 3) / 10 = 2.3
        assert r["neff_ratio"] == pytest.approx(2.3, abs=0.1)
        assert r["neff_score"] == 3  # >1.5

    def test_high_neff(self):
        # EPS: 500→1000 (100% CAGR, 1 year)
        r = calc_neff([500, 1000], dividend_yield=5.0, per=8.0)
        assert r["calculable"] is True
        # Neff = (100 + 5) / 8 = 13.125
        assert r["neff_ratio"] > 2.5
        assert r["neff_score"] == 4

    def test_per_negative(self):
        r = calc_neff([1000, 1200], dividend_yield=3.0, per=-5.0)
        assert r["calculable"] is False

    def test_per_too_high(self):
        r = calc_neff([1000, 1200], dividend_yield=3.0, per=50.0)
        assert r["calculable"] is False

    def test_insufficient_eps(self):
        r = calc_neff([1000], dividend_yield=3.0, per=10.0)
        assert r["calculable"] is False

    def test_eps_with_negatives(self):
        # 음수 EPS는 필터링됨 → 유효한 게 1개뿐이면 불가
        r = calc_neff([-100, 500], dividend_yield=3.0, per=10.0)
        assert r["calculable"] is False

    def test_no_dividend(self):
        r = calc_neff([1000, 1200, 1440], dividend_yield=None, per=10.0)
        assert r["calculable"] is True
        # 배당 0으로 처리
        assert r["neff_ratio"] > 0


# ── 서준식 기대수익률 ────────────────────────────────────────────

class TestSeoExpectedReturn:
    def test_roe_pbr_basic(self):
        r = calc_seo_expected_return(roe=15.0, pbr=1.0)
        assert r["calculable"] is True
        assert r["expected_return"] == 15.0
        assert r["method"] == "roe_pbr"
        assert r["seo_score"] == 4  # >12%

    def test_roe_pbr_low(self):
        r = calc_seo_expected_return(roe=6.0, pbr=1.5)
        assert r["calculable"] is True
        assert r["expected_return"] == 4.0
        assert r["seo_score"] == 1  # <5%

    def test_pbr_zero_fallback_to_per(self):
        r = calc_seo_expected_return(roe=10.0, pbr=0.0, per=8.0, dividend_yield=2.0)
        assert r["calculable"] is True
        assert r["method"] == "per_dividend"
        # (1/8)*100 + 2 = 14.5
        assert r["expected_return"] == pytest.approx(14.5, abs=0.01)

    def test_all_none(self):
        r = calc_seo_expected_return(roe=None, pbr=None, per=None)
        assert r["calculable"] is False

    def test_pbr_none_per_available(self):
        r = calc_seo_expected_return(roe=None, pbr=None, per=10.0, dividend_yield=3.0)
        assert r["calculable"] is True
        assert r["method"] == "per_dividend"
        # (1/10)*100 + 3 = 13.0
        assert r["expected_return"] == 13.0


# ── Graham NCAV ──────────────────────────────────────────────────

class TestGrahamNCAV:
    def test_net_net(self):
        r = calc_graham_ncav(
            current_assets=5_000_000_000,
            total_liabilities=2_000_000_000,
            mktcap=2_000_000_000,
        )
        assert r["calculable"] is True
        # NCAV = 50억 - 20억 = 30억, ratio = 30/20 = 1.5
        assert r["ncav_ratio"] == 1.5
        assert r["ncav_score"] == 4  # >= 1.5

    def test_ncav_negative(self):
        r = calc_graham_ncav(
            current_assets=1_000_000_000,
            total_liabilities=3_000_000_000,
            mktcap=5_000_000_000,
        )
        assert r["calculable"] is False
        assert r["ncav_score"] == 1

    def test_missing_data(self):
        r = calc_graham_ncav(None, None, 1_000_000)
        assert r["calculable"] is False

    def test_score_tiers(self):
        # ratio 1.0 → 3점
        r = calc_graham_ncav(3_000, 1_000, 2_000)
        assert r["ncav_score"] == 3
        # ratio 0.5 → 2점
        r = calc_graham_ncav(2_000, 1_000, 2_000)
        assert r["ncav_score"] == 2


# ── Fisher PSR ───────────────────────────────────────────────────

class TestFisherPSR:
    def test_strong_buy(self):
        # PSR = 500 / 1000 = 0.5
        r = calc_fisher_psr(mktcap=500, revenue=1000)
        assert r["calculable"] is True
        assert r["psr"] == 0.5
        assert r["psr_score"] == 4  # < 0.75

    def test_moderate(self):
        # PSR = 1200 / 1000 = 1.2
        r = calc_fisher_psr(mktcap=1200, revenue=1000)
        assert r["psr_score"] == 2  # < 1.5

    def test_overvalued(self):
        # PSR = 2000 / 1000 = 2.0
        r = calc_fisher_psr(mktcap=2000, revenue=1000)
        assert r["psr_score"] == 1  # >= 1.5

    def test_zero_revenue(self):
        r = calc_fisher_psr(mktcap=1000, revenue=0)
        assert r["calculable"] is False

    def test_missing(self):
        r = calc_fisher_psr(mktcap=None, revenue=1000)
        assert r["calculable"] is False


# ── Piotroski F-Score ────────────────────────────────────────────

class TestPiotroskiFScore:
    def _make_data(self, **overrides):
        """2개년 테스트 데이터 생성."""
        defaults = dict(
            bs_prev={"total_assets": 1000, "total_equity": 600, "total_liabilities": 400,
                      "current_assets": 500, "current_liabilities": 200,
                      "debt_ratio": 66.7, "current_ratio": 250.0},
            bs_cur={"total_assets": 1100, "total_equity": 700, "total_liabilities": 400,
                     "current_assets": 600, "current_liabilities": 200,
                     "debt_ratio": 57.1, "current_ratio": 300.0},
            cf_cur={"operating_cf": 150},
            is_prev={"revenue": 800, "gross_profit": 400, "net_income": 80},
            is_cur={"revenue": 1000, "gross_profit": 550, "net_income": 120},
        )
        defaults.update(overrides)
        return defaults

    def test_perfect_score(self):
        d = self._make_data()
        r = calc_piotroski_fscore(
            bs_list=[d["bs_prev"], d["bs_cur"]],
            cf_list=[d["cf_cur"]],
            is_list=[d["is_prev"], d["is_cur"]],
        )
        assert r["calculable"] is True
        assert r["fscore"] == 8  # 모든 항목 충족
        assert r["fscore_score"] == 4

    def test_low_score(self):
        d = self._make_data(
            bs_cur={"total_assets": 1000, "total_equity": 400, "total_liabilities": 600,
                     "current_assets": 300, "current_liabilities": 400,
                     "debt_ratio": 150.0, "current_ratio": 75.0},
            cf_cur={"operating_cf": -50},
            is_cur={"revenue": 700, "gross_profit": 300, "net_income": -20},
        )
        r = calc_piotroski_fscore(
            bs_list=[d["bs_prev"], d["bs_cur"]],
            cf_list=[d["cf_cur"]],
            is_list=[d["is_prev"], d["is_cur"]],
        )
        assert r["fscore"] <= 2
        assert r["fscore_score"] == 1

    def test_insufficient_data(self):
        r = calc_piotroski_fscore(
            bs_list=[{"total_assets": 100}],
            cf_list=[],
            is_list=[{"revenue": 50}],
        )
        assert r["calculable"] is False


# ── 구루 패널 ────────────────────────────────────────────────────

class TestGuruPanel:
    def test_all_six(self):
        gb = {"calculable": True, "total_score": 6}
        nf = {"calculable": True, "neff_score": 3}
        seo = {"calculable": True, "seo_score": 4}
        ncav = {"calculable": True, "ncav_score": 3}
        fisher = {"calculable": True, "psr_score": 4}
        pio = {"calculable": True, "fscore_score": 3}
        panel = calc_guru_panel(gb, nf, seo, ncav, fisher, pio)
        assert panel["formulas_available"] == 6
        assert panel["max_possible"] == 24
        # gb:3 + neff:3 + seo:4 + ncav:3 + fisher:4 + pio:3 = 20
        assert panel["total_score"] == 20

    def test_all_three_legacy(self):
        gb = {"calculable": True, "total_score": 6}
        nf = {"calculable": True, "neff_score": 3}
        seo = {"calculable": True, "seo_score": 4}
        panel = calc_guru_panel(gb, nf, seo)
        assert panel["formulas_available"] == 3
        assert panel["max_possible"] == 12
        assert panel["total_score"] == 10

    def test_only_seo(self):
        panel = calc_guru_panel(None, None, {"calculable": True, "seo_score": 3})
        assert panel["formulas_available"] == 1
        assert panel["max_possible"] == 4
        assert panel["total_score"] == 3
        assert panel["normalized_score"] == 75.0

    def test_none_available(self):
        panel = calc_guru_panel(None, None, None)
        assert panel["formulas_available"] == 0
        assert panel["normalized_score"] == 0

    def test_not_calculable(self):
        gb = {"calculable": False, "total_score": 2}
        panel = calc_guru_panel(gb, None, None)
        assert panel["formulas_available"] == 0

    def test_greenblatt_max_normalization(self):
        gb = {"calculable": True, "total_score": 8}
        panel = calc_guru_panel(gb, None, None)
        assert panel["total_score"] == 4


# ── Value Trap ───────────────────────────────────────────────────

class TestValueTrap:
    def test_no_warnings(self):
        w = check_value_trap(per=12.0, pbr=1.2, roe=15.0,
                             revenue_cagr=5.0, fcf_years_positive=3, debt_ratio=50.0)
        assert w == []

    def test_low_pbr_low_roe(self):
        w = check_value_trap(per=None, pbr=0.3, roe=2.0,
                             revenue_cagr=None, fcf_years_positive=None, debt_ratio=None)
        assert any("저PBR+저ROE" in x for x in w)

    def test_low_per_negative_cagr(self):
        w = check_value_trap(per=3.0, pbr=None, roe=None,
                             revenue_cagr=-10.0, fcf_years_positive=None, debt_ratio=None)
        assert any("저PER+매출역성장" in x for x in w)

    def test_fcf_zero(self):
        w = check_value_trap(per=None, pbr=None, roe=None,
                             revenue_cagr=None, fcf_years_positive=0, debt_ratio=None)
        assert any("FCF" in x for x in w)

    def test_high_debt(self):
        w = check_value_trap(per=None, pbr=None, roe=None,
                             revenue_cagr=None, fcf_years_positive=None, debt_ratio=250.0)
        assert any("부채비율" in x for x in w)

    def test_low_pbr_high_debt(self):
        w = check_value_trap(per=None, pbr=0.5, roe=None,
                             revenue_cagr=None, fcf_years_positive=None, debt_ratio=180.0)
        assert any("저PBR+고부채" in x for x in w)

    def test_multiple_warnings(self):
        w = check_value_trap(per=3.0, pbr=0.4, roe=1.0,
                             revenue_cagr=-8.0, fcf_years_positive=0, debt_ratio=210.0)
        assert len(w) >= 3

    def test_fscore_extreme_low(self):
        w = check_value_trap(per=None, pbr=None, roe=None,
                             revenue_cagr=None, fcf_years_positive=None,
                             debt_ratio=None, fscore=1)
        assert any("F-Score" in x for x in w)

    def test_low_psr_declining_revenue(self):
        w = check_value_trap(per=None, pbr=None, roe=None,
                             revenue_cagr=-15.0, fcf_years_positive=None,
                             debt_ratio=None, psr=0.3)
        assert any("극저PSR" in x for x in w)


# ── 체제별 파라미터 ──────────────────────────────────────────────

class TestRegimeGuruParams:
    def test_all_regimes_exist(self):
        for regime in ("accumulation", "selective", "cautious", "defensive"):
            assert regime in REGIME_GURU_PARAMS

    def test_defensive_blocks(self):
        d = REGIME_GURU_PARAMS["defensive"]
        assert d["greenblatt_roic_min"] == 999
        assert d["neff_ratio_min"] == 999

    def test_accumulation_most_lenient(self):
        a = REGIME_GURU_PARAMS["accumulation"]
        s = REGIME_GURU_PARAMS["selective"]
        assert a["greenblatt_roic_min"] < s["greenblatt_roic_min"]
        assert a["neff_ratio_min"] < s["neff_ratio_min"]
        assert a["seo_return_min"] < s["seo_return_min"]

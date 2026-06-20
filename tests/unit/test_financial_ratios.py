"""services/financial_ratios.py 4축 재무비율 평가 테스트.

REQ-MARGIN-01(진입점) / REQ-MARGIN-02(활동성) / REQ-SCREEN-01(성장성) /
REQ-MARGIN-03(수익성) / REQ-MARGIN-04(안정성) / REQ-DIAG-01(진단).

도메인 결정 §D-1~§D-7 + 임계값 보정 확정값 검증.
순수 함수 (외부 호출 0). 리스트는 오래된순(과거→최신) 정렬.
"""

import importlib

from services import financial_ratios as fr


# ────────────────────────── 헬퍼 ──────────────────────────

def _income(revenue=None, oi=None, ni=None, cogs=None, ie=None):
    d = {}
    if revenue is not None: d["revenue"] = revenue
    if oi is not None: d["operating_income"] = oi
    if ni is not None: d["net_income"] = ni
    if cogs is not None: d["cogs"] = cogs
    if ie is not None: d["interest_expense"] = ie
    return d


def _bs(ta=None, ca=None, recv=None, inv=None, pay=None, tl=None, cl=None,
        std=None, ltd=None, te=None):
    d = {}
    for k, v in [("total_assets", ta), ("current_assets", ca), ("receivables", recv),
                 ("inventories", inv), ("payables", pay), ("total_liabilities", tl),
                 ("current_liabilities", cl), ("short_term_debt", std),
                 ("long_term_debt", ltd), ("total_equity", te)]:
        if v is not None:
            d[k] = v
    return d


# ═══════════════════ REQ-MARGIN-01: 진입점 / shape ═══════════════════

def test_import_no_side_effects():
    """import 부수효과 0 — 재import 가능."""
    importlib.reload(fr)
    assert hasattr(fr, "compute_ratio_analysis")


def test_full_manufacturing_shape():
    """완전한 3개년 제조업 → overall_score float, 4축 applicable, 16비율 None 0개."""
    income = [
        _income(revenue=100, oi=20, ni=15, cogs=60, ie=2),
        _income(revenue=110, oi=22, ni=17, cogs=66, ie=2),
        _income(revenue=121, oi=25, ni=20, cogs=70, ie=2),
    ]
    bs = [
        _bs(ta=200, ca=120, recv=40, inv=30, pay=25, tl=80, cl=60, std=10, ltd=10, te=120),
        _bs(ta=220, ca=130, recv=42, inv=28, pay=24, tl=85, cl=62, std=10, ltd=10, te=135),
        _bs(ta=240, ca=140, recv=44, inv=26, pay=22, tl=90, cl=64, std=10, ltd=10, te=150),
    ]
    cf = [{"operating_cf": 18}, {"operating_cf": 20}, {"operating_cf": 23}]
    metrics = {"oi_margin": 20.6, "roe": 13.3, "debt_ratio": 60, "current_ratio": 140}

    result = fr.compute_ratio_analysis(income, bs, cf, metrics, sector_tier="general")

    assert isinstance(result["overall_score"], float)
    assert result["overall_grade"] in ("우수", "양호", "보통", "주의", "위험")
    assert list(result["axes"].keys()) == ["activity", "growth", "profitability", "stability"]
    for axis in result["axes"].values():
        assert axis["applicable"] is True
    assert result["sector_tier"] == "general"
    assert result["meta"]["method"] == "ratio_4axis_v1"
    assert result["meta"]["valid_axis_count"] == 4


def test_empty_inputs_all_na():
    """모든 입력 빈 + metrics={} → overall None, grade N/A, 4축 applicable=False."""
    result = fr.compute_ratio_analysis([], [], [], {}, sector_tier="general")
    assert result["overall_score"] is None
    assert result["overall_grade"] == "N/A"
    for axis in result["axes"].values():
        assert axis["applicable"] is False


def test_axes_order_fixed():
    """축 순서 고정: activity → growth → profitability → stability."""
    result = fr.compute_ratio_analysis([], [], [], {})
    assert list(result["axes"].keys()) == ["activity", "growth", "profitability", "stability"]


# ═══════════════════ REQ-MARGIN-02: 활동성 (추세 채점) ═══════════════════

def test_activity_total_asset_turnover_rising():
    """총자산회전율 [0.8, 0.9, 1.05] → normalized slope ~13.6% > +10 → 4점.

    (요건서 1차 힌트 [0.8,0.85,0.92]는 정규화 기울기 7.0%로 실제 3점 — §D-2 정규화
    공식상 완만 상승 밴드. 뚜렷한 상승 4점 의도를 보존하도록 입력 보정.)
    """
    income = [_income(revenue=80), _income(revenue=90), _income(revenue=105)]
    bs = [_bs(ta=100), _bs(ta=100), _bs(ta=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    pts = result["axes"]["activity"]["ratios"]["total_asset_turnover"]["points"]
    assert pts == 4


def test_activity_inventory_turnover_declining():
    """재고자산회전율 [10, 8, 6] (악화) → normalized < -5 → 1점."""
    income = [_income(cogs=100), _income(cogs=80), _income(cogs=60)]
    bs = [_bs(inv=10), _bs(inv=10), _bs(inv=10)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    pts = result["axes"]["activity"]["ratios"]["inventory_turnover"]["points"]
    assert pts == 1


def test_activity_inventories_all_none_skipped():
    """inventories 전부 None → 재고자산회전율 None, 나머지 비율로 축 평균."""
    income = [_income(revenue=80, cogs=60), _income(revenue=85, cogs=63),
              _income(revenue=92, cogs=66)]
    bs = [_bs(ta=100, recv=40, pay=20), _bs(ta=100, recv=40, pay=20),
          _bs(ta=100, recv=40, pay=20)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    inv_pts = result["axes"]["activity"]["ratios"]["inventory_turnover"]["points"]
    assert inv_pts is None
    assert result["axes"]["activity"]["applicable"] is True


def test_activity_less_than_two_points_none():
    """유효 시계열 < 2점 → 비율 점수 None."""
    income = [_income(revenue=80)]
    bs = [_bs(ta=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    assert result["axes"]["activity"]["ratios"]["total_asset_turnover"]["points"] is None


def test_activity_trend_pct_exposed():
    """trend_pct 노출 (UI 펼침용)."""
    income = [_income(revenue=80), _income(revenue=90), _income(revenue=105)]
    bs = [_bs(ta=100), _bs(ta=100), _bs(ta=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    tp = result["axes"]["activity"]["ratios"]["total_asset_turnover"]["trend_pct"]
    assert tp is not None and tp > 10


def test_activity_two_year_fallback_simple_change():
    """2개년만 → 단순 변화율 fallback."""
    income = [_income(revenue=80), _income(revenue=92)]
    bs = [_bs(ta=100), _bs(ta=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    # (0.92-0.8)/0.8*100 = +15 → >+10 → 4점
    assert result["axes"]["activity"]["ratios"]["total_asset_turnover"]["points"] == 4


def test_activity_boundary_flat_band():
    """보합 [-5, 0] → 2점. 완만 상승 0~+10 → 3점."""
    # 완만 상승: [1.0, 1.03, 1.06] → normalized ~ +3 → 3점
    income = [_income(revenue=100), _income(revenue=103), _income(revenue=106)]
    bs = [_bs(ta=100), _bs(ta=100), _bs(ta=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    assert result["axes"]["activity"]["ratios"]["total_asset_turnover"]["points"] == 3


# ═══════════════════ REQ-SCREEN-01: 성장성 (CAGR 채점) ═══════════════════

def test_growth_revenue_cagr_10pct():
    """revenue [100, 110, 121] CAGR=10% → 3점."""
    income = [_income(revenue=100), _income(revenue=110), _income(revenue=121)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["growth"]["ratios"]["revenue_growth"]["points"] == 3


def test_growth_net_income_first_negative_none():
    """net_income [-50, 20, 30] (first 음수) → 순이익 증가율 None."""
    income = [_income(ni=-50), _income(ni=20), _income(ni=30)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["growth"]["ratios"]["net_income_growth"]["points"] is None


def test_growth_total_assets_2year():
    """total_assets [1000, 1500] (+50%) → 4점."""
    bs = [_bs(ta=1000), _bs(ta=1500)]
    result = fr.compute_ratio_analysis([], bs, [], {})
    assert result["axes"]["growth"]["ratios"]["total_asset_growth"]["points"] == 4


def test_growth_one_year_none():
    """1개년 → CAGR None."""
    income = [_income(revenue=100)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["growth"]["ratios"]["revenue_growth"]["points"] is None


def test_growth_negative_cagr_one_point():
    """CAGR < 0 → 1점."""
    income = [_income(revenue=121), _income(revenue=110), _income(revenue=100)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["growth"]["ratios"]["revenue_growth"]["points"] == 1


# ═══════════════════ REQ-MARGIN-03: 수익성 (절대 임계값) ═══════════════════

def test_profitability_all_3points():
    """oi_margin=12, ROE=10, ROA=5, interest_coverage=4 → 3,3,3,3 → 75 양호."""
    income = [_income(revenue=100, oi=12, ni=5, ie=3)]
    bs = [_bs(ta=100, te=50)]  # ROA = 5/100*100 = 5
    metrics = {"oi_margin": 12, "roe": 10}
    result = fr.compute_ratio_analysis(income, bs, [], metrics)
    prof = result["axes"]["profitability"]
    assert prof["ratios"]["oi_margin"]["points"] == 3
    assert prof["ratios"]["roe"]["points"] == 3
    assert prof["ratios"]["roa"]["points"] == 3
    assert prof["ratios"]["interest_coverage"]["points"] == 3
    assert prof["score"] == 75.0
    assert prof["grade"] == "양호"


def test_profitability_zero_interest_expense_4points():
    """interest_expense=0, operating_income=100 → 이자보상 4점 (무차입 우량)."""
    income = [_income(revenue=100, oi=100, ie=0)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] == 4


def test_profitability_none_interest_expense_is_none():
    """interest_expense None(파싱 실패) + 영업흑자 → None (bug_004 보정).

    이전엔 '무차입 우량 4점'을 줬으나, None은 무차입(0)이 아니라 DART 라벨 변형
    파싱 실패일 수 있어 4점 false-positive였음. 실측 무차입은 ie=0으로 표현
    (test_ic_ie_zero_with_op_profit_is_4 참조).
    """
    income = [_income(revenue=100, oi=50)]  # ie 미지정 → None
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] is None


def test_profitability_zero_interest_operating_loss_1point():
    """실측 무차입(ie=0) + 영업적자 → 1점."""
    income = [_income(revenue=100, oi=-10, ie=0)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] == 1


def test_profitability_roa_thresholds():
    """ROA 임계: >7=4, 3~7=3, 0~3=2, <0=1."""
    # ROA = ni/ta*100
    r4 = fr.compute_ratio_analysis([_income(ni=8)], [_bs(ta=100)], [], {})
    assert r4["axes"]["profitability"]["ratios"]["roa"]["points"] == 4
    r1 = fr.compute_ratio_analysis([_income(ni=-5)], [_bs(ta=100)], [], {})
    assert r1["axes"]["profitability"]["ratios"]["roa"]["points"] == 1


def test_profitability_interest_coverage_corrected_thresholds():
    """이자보상비율 보정: >5=4, 3~5=3, 1~3=2, <1=1."""
    # coverage = oi/ie
    r2 = fr.compute_ratio_analysis([_income(oi=20, ie=10)], [], [], {})  # 2.0배 → 2점
    assert r2["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] == 2
    r3 = fr.compute_ratio_analysis([_income(oi=40, ie=10)], [], [], {})  # 4.0배 → 3점
    assert r3["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] == 3


def test_profitability_securities_only_roe_roa():
    """securities → ROE/ROA 2비율만. ROE=9(3점)/ROA=2(2점) → 62.5."""
    income = [_income(ni=2)]
    bs = [_bs(ta=100, te=50)]
    metrics = {"roe": 9}
    result = fr.compute_ratio_analysis(income, bs, [], metrics, sector_tier="securities")
    prof = result["axes"]["profitability"]
    assert prof["ratios"]["roe"]["points"] == 3
    assert prof["ratios"]["roa"]["points"] == 2
    # 영업이익률/이자보상 제외
    assert prof["ratios"].get("oi_margin", {}).get("points") is None
    assert prof["score"] == 62.5


def test_profitability_latest_fallback():
    """latest None이면 직전 연도 fallback 1회 (ROA)."""
    income = [_income(ni=8), _income()]  # latest ni None
    bs = [_bs(ta=100), _bs(ta=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    # 직전 ni=8, ta=100 → ROA 8 → 4점
    assert result["axes"]["profitability"]["ratios"]["roa"]["points"] == 4


# ═════════ ultrareview 결함 수정: bug_004 이자보상 None↔0 (도메인 확정) ═════════

def test_ic_ie_none_with_bs_debt_is_none_not_4():
    """[bug_004] interest_expense 파싱 실패(None) + BS 차입금 보유 → None (4점 false-positive 차단).

    DART 라벨 변형('이자비용계' 등)으로 ie=None인데 차입금이 명백히 있으면
    '무차입 우량 4점'은 잘못된 신호. §D-6 결손 정책에 따라 비율 None(평균 skip).
    """
    income = [_income(revenue=100, oi=50)]  # ie 없음(None), 영업흑자
    bs = [_bs(ta=200, std=30, ltd=20)]  # 차입금 50 보유
    result = fr.compute_ratio_analysis(income, bs, [], {})
    ic = result["axes"]["profitability"]["ratios"]["interest_coverage"]
    assert ic["points"] is None, f"차입보유+ie None은 None이어야 함, got {ic}"


def test_ic_ie_zero_with_op_profit_is_4():
    """[bug_004] interest_expense == 0(실측 무차입) + 영업흑자 → 4점 유지(회귀 가드)."""
    income = [_income(revenue=100, oi=100, ie=0)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] == 4


def test_ic_ie_none_no_bs_debt_info_is_none():
    """[bug_004] ie None + BS 차입 항목도 전부 None(판별 불가) → 보수적 None.

    차입 유무를 판별할 근거가 없으면 4점을 부여하지 않는다(Graham 보수주의).
    """
    income = [_income(revenue=100, oi=50)]
    bs = [_bs(ta=200)]  # std/ltd 둘 다 None
    result = fr.compute_ratio_analysis(income, bs, [], {})
    assert result["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] is None


def test_ic_ie_zero_operating_loss_is_1():
    """[bug_004] ie == 0 + 영업적자 → 1점 유지(회귀 가드)."""
    income = [_income(revenue=100, oi=-10, ie=0)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    assert result["axes"]["profitability"]["ratios"]["interest_coverage"]["points"] == 1


# ═════════ ultrareview 결함 수정: bug_011 ROE metrics None fallback ═════════

def test_roe_fallback_from_is_bs_when_metrics_none():
    """[bug_011] metrics.roe None + IS/BS 존재 → latest net_income/total_equity×100 산출.

    oi_margin은 latest fallback이 있는데 ROE는 metrics 단일 경로라 비대칭이었음.
    ROE 분모 = 자기자본(MarginAnalyst 확정).
    """
    income = [_income(ni=20)]
    bs = [_bs(ta=100, te=100)]  # ROE = 20/100*100 = 20 → >15 → 4점
    result = fr.compute_ratio_analysis(income, bs, [], {})  # metrics 비어있음
    roe = result["axes"]["profitability"]["ratios"]["roe"]
    assert roe["value"] == 20.0
    assert roe["points"] == 4


def test_roe_fallback_equity_deficit_is_none():
    """[bug_011] metrics.roe None + total_equity ≤ 0(자본잠식) → ROE None(분모 보호)."""
    income = [_income(ni=-20)]
    bs = [_bs(ta=100, te=-50)]
    result = fr.compute_ratio_analysis(income, bs, [], {})
    assert result["axes"]["profitability"]["ratios"]["roe"]["points"] is None


def test_roe_metrics_takes_priority_over_fallback():
    """[bug_011] metrics.roe 존재 시 fallback 미사용(우선순위 회귀 가드)."""
    income = [_income(ni=20)]
    bs = [_bs(ta=100, te=100)]
    result = fr.compute_ratio_analysis(income, bs, [], {"roe": 5})  # metrics 우선
    assert result["axes"]["profitability"]["ratios"]["roe"]["value"] == 5.0
    assert result["axes"]["profitability"]["ratios"]["roe"]["points"] == 2


# ═══════════════════ REQ-MARGIN-04: 안정성 (절대 임계값) ═══════════════════

def test_stability_all_high():
    """debt_ratio=90, 자기자본비율=53, 차입의존도=12, 유동비율=140 → 4,4,4,3 → 93.75 우수."""
    bs = [_bs(ta=100, te=53, tl=90, std=6, ltd=6, ca=140, cl=100)]
    metrics = {"debt_ratio": 90, "current_ratio": 140}
    result = fr.compute_ratio_analysis([], bs, [], metrics)
    stab = result["axes"]["stability"]
    assert stab["ratios"]["debt_ratio"]["points"] == 4
    assert stab["ratios"]["equity_ratio"]["points"] == 4
    assert stab["ratios"]["debt_dependency"]["points"] == 4
    assert stab["ratios"]["current_ratio"]["points"] == 3
    assert stab["score"] == 93.75
    assert stab["grade"] == "우수"


def test_stability_debt_ratio_danger():
    """debt_ratio=300 (>250) → 1점."""
    result = fr.compute_ratio_analysis([], [_bs(tl=300, te=100)], [], {"debt_ratio": 300})
    assert result["axes"]["stability"]["ratios"]["debt_ratio"]["points"] == 1


def test_stability_current_ratio_multiple_unit():
    """current_ratio=1.4 (배수, ≤10) → 140%로 환산 → 3점."""
    result = fr.compute_ratio_analysis([], [], [], {"current_ratio": 1.4})
    assert result["axes"]["stability"]["ratios"]["current_ratio"]["points"] == 3


def test_stability_current_ratio_pct_unit():
    """current_ratio=140 (%, >10) → 그대로 3점."""
    result = fr.compute_ratio_analysis([], [], [], {"current_ratio": 140})
    assert result["axes"]["stability"]["ratios"]["current_ratio"]["points"] == 3


def test_stability_debt_dependency_both_none_4points():
    """short/long term debt 둘 다 None → 무차입 0% → 4점 (total_assets 존재 시)."""
    result = fr.compute_ratio_analysis([], [_bs(ta=100)], [], {})
    assert result["axes"]["stability"]["ratios"]["debt_dependency"]["points"] == 4


def test_stability_debt_dependency_none_assets_none():
    """total_assets None이면 차입의존도 None."""
    result = fr.compute_ratio_analysis([], [_bs(te=50)], [], {})
    assert result["axes"]["stability"]["ratios"]["debt_dependency"]["points"] is None


def test_stability_equity_ratio_thresholds():
    """자기자본비율: >50=4, 35~50=3, 20~35=2, <20=1."""
    r3 = fr.compute_ratio_analysis([], [_bs(ta=100, te=40)], [], {})
    assert r3["axes"]["stability"]["ratios"]["equity_ratio"]["points"] == 3
    r1 = fr.compute_ratio_analysis([], [_bs(ta=100, te=15)], [], {})
    assert r1["axes"]["stability"]["ratios"]["equity_ratio"]["points"] == 1


def test_stability_debt_dependency_thresholds():
    """차입금의존도: <15=4, 15~30=3, 30~45=2, >45=1."""
    r2 = fr.compute_ratio_analysis([], [_bs(ta=100, std=20, ltd=15)], [], {})  # 35% → 2점
    assert r2["axes"]["stability"]["ratios"]["debt_dependency"]["points"] == 2
    r1 = fr.compute_ratio_analysis([], [_bs(ta=100, std=30, ltd=20)], [], {})  # 50% → 1점
    assert r1["axes"]["stability"]["ratios"]["debt_dependency"]["points"] == 1


# ═════════ ultrareview 결함 수정: bug_015 자본잠식 부채비율 sentinel ═════════

def test_stability_equity_deficit_debt_ratio_sentinel_1point():
    """[bug_015] total_equity ≤ 0(자본잠식) → 부채비율 1점 강제(metrics 음수값보다 우선).

    yfinance가 부채/음수자본으로 음수 debt_ratio(-1100 등)를 주면 -1100<100 → 4점
    false-positive. 자본잠식은 관리종목 1차 트리거 = 강한 부실 신호 → sentinel 1점.
    """
    bs = [_bs(ta=100, te=-50, tl=150)]
    metrics = {"debt_ratio": -1100}  # yfinance 음수 비정상값
    result = fr.compute_ratio_analysis([], bs, [], metrics)
    stab = result["axes"]["stability"]
    assert stab["ratios"]["debt_ratio"]["points"] == 1, "자본잠식 부채비율은 sentinel 1점"


def test_stability_equity_deficit_caps_axis_below_caution():
    """[bug_015] 자본잠식 시 자기자본비율(음수→1점)+부채비율(sentinel 1점) → 안정성 '주의' 이하.

    이전: debt_ratio 4점 false-positive로 75점 '양호' (관리종목인데 양호 표시).
    """
    bs = [_bs(ta=100, te=-50, tl=150)]
    metrics = {"debt_ratio": -1100}
    result = fr.compute_ratio_analysis([], bs, [], metrics)
    stab = result["axes"]["stability"]
    assert stab["ratios"]["equity_ratio"]["points"] == 1
    assert stab["ratios"]["debt_ratio"]["points"] == 1
    # 안정성 등급이 '양호'/'우수'로 잘못 부풀지 않음
    assert stab["grade"] in ("주의", "위험", "보통")
    assert stab["score"] <= 69


def test_stability_equity_deficit_diagnosis_flag():
    """[bug_015] 자본잠식 시 진단에 '자본잠식' 별도 표기 + 강한 부실 신호."""
    bs = [_bs(ta=100, te=-50, tl=150)]
    metrics = {"debt_ratio": -1100}
    result = fr.compute_ratio_analysis([], bs, [], metrics)
    diag = result["axes"]["stability"]["diagnosis"]
    assert "자본잠식" in diag


def test_stability_positive_equity_debt_ratio_unaffected():
    """[bug_015] 정상 자본(te>0)은 sentinel 미적용(회귀 가드)."""
    bs = [_bs(ta=100, te=50, tl=80)]
    metrics = {"debt_ratio": 80}  # 정상 → 4점
    result = fr.compute_ratio_analysis([], bs, [], metrics)
    assert result["axes"]["stability"]["ratios"]["debt_ratio"]["points"] == 4


# ═══════════════════ §D-5 금융업 분기 ═══════════════════

def test_bank_holding_activity_na():
    """bank_holding → activity.applicable=False + na_reason, overall은 나머지 3축 평균."""
    income = [_income(revenue=100, ni=10), _income(revenue=110, ni=12)]
    bs = [_bs(ta=1000, te=100), _bs(ta=1100, te=120)]
    metrics = {"roe": 12}
    result = fr.compute_ratio_analysis(income, bs, [], metrics, sector_tier="bank_holding")
    assert result["axes"]["activity"]["applicable"] is False
    assert result["axes"]["activity"]["na_reason"] is not None
    assert result["meta"]["valid_axis_count"] <= 3


def test_insurance_equity_ratio_kics_threshold():
    """insurance 자기자본비율 K-ICS: >15=4/10-15=3/5-10=2/<5=1. 자본비율=12 → 3점, 단일 → 75."""
    bs = [_bs(ta=100, te=12)]
    result = fr.compute_ratio_analysis([], bs, [], {}, sector_tier="insurance")
    stab = result["axes"]["stability"]
    assert stab["ratios"]["equity_ratio"]["points"] == 3
    assert stab["score"] == 75.0
    # 부채비율/차입의존도/유동비율 제외
    assert stab["ratios"].get("debt_ratio", {}).get("points") is None


def test_bank_holding_equity_ratio_bis_threshold():
    """bank_holding 자기자본비율 BIS: >12=4/8-12=3/4-8=2/<4=1. 자본비율=10 → 3점."""
    bs = [_bs(ta=100, te=10)]
    result = fr.compute_ratio_analysis([], bs, [], {}, sector_tier="bank_holding")
    assert result["axes"]["stability"]["ratios"]["equity_ratio"]["points"] == 3


def test_financial_profitability_excludes_oi_and_coverage():
    """금융업 수익성: ROE/ROA만."""
    income = [_income(revenue=100, oi=50, ni=10, ie=5)]
    bs = [_bs(ta=100, te=50)]
    metrics = {"roe": 12, "oi_margin": 50}
    result = fr.compute_ratio_analysis(income, bs, [], metrics, sector_tier="securities")
    prof = result["axes"]["profitability"]
    assert prof["ratios"].get("oi_margin", {}).get("points") is None
    assert prof["ratios"].get("interest_coverage", {}).get("points") is None
    assert prof["ratios"]["roe"]["points"] is not None


# ═══════════════════ REQ-DIAG-01: 진단 문구 ═══════════════════

def test_diag_stability_low_points_to_weakest():
    """안정성 score<50, 차입금의존도 최저 → '자금조달 능력 저하 — 특히 차입금의존도 취약'."""
    # debt_ratio 300(1), equity 15(1), dependency 50(1), current 90(1) → 25 → danger
    bs = [_bs(ta=100, te=15, tl=300, std=30, ltd=20, ca=90, cl=100)]
    metrics = {"debt_ratio": 300, "current_ratio": 90}
    result = fr.compute_ratio_analysis([], bs, [], metrics)
    diag = result["axes"]["stability"]["diagnosis"]
    assert "자금조달 능력 저하" in diag


def test_diag_profitability_excellent():
    """수익성 score≥85 → '수익성 우수'."""
    income = [_income(revenue=100, oi=20, ni=10, ie=1)]
    bs = [_bs(ta=100, te=50)]
    metrics = {"oi_margin": 20, "roe": 20}
    result = fr.compute_ratio_analysis(income, bs, [], metrics)
    diag = result["axes"]["profitability"]["diagnosis"]
    assert "우수" in diag


def test_diag_activity_na_financial():
    """활동성 N/A(금융) → '해당 업종 적용 불가(N/A)'."""
    result = fr.compute_ratio_analysis([], [_bs(ta=100, te=50)], [], {"roe": 10},
                                       sector_tier="bank_holding")
    diag = result["axes"]["activity"]["diagnosis"]
    assert "N/A" in diag or "적용 불가" in diag


def test_diag_no_trade_action_keywords():
    """진단 문구에 매매 액션 키워드 부재 (§D-7 회귀 가드)."""
    income = [_income(revenue=121, oi=-10, ni=-5),
              _income(revenue=110, oi=-8, ni=-4),
              _income(revenue=100, oi=-6, ni=-3)]
    bs = [_bs(ta=100, te=10, tl=300, std=30, ltd=20, ca=80, cl=100)] * 3
    metrics = {"oi_margin": -6, "roe": -5, "debt_ratio": 300, "current_ratio": 80}
    result = fr.compute_ratio_analysis(income, bs, [], metrics)
    banned = ["recommendation", "action", "buy", "sell", "order", "매수", "매도"]
    for axis in result["axes"].values():
        diag = axis.get("diagnosis", "") or ""
        for kw in banned:
            assert kw.lower() not in diag.lower(), f"banned keyword '{kw}' in: {diag}"


def test_diag_no_action_keys_in_response():
    """응답 dict 어디에도 매매 액션 키 부재 (§D-7)."""
    import json
    income = [_income(revenue=100, oi=20, ni=15, cogs=60, ie=2)]
    bs = [_bs(ta=200, te=120, tl=80, ca=120, cl=60, std=10, ltd=10, recv=40, inv=30, pay=20)]
    result = fr.compute_ratio_analysis(income, bs, [], {"oi_margin": 20, "roe": 13})
    dumped = json.dumps(result, ensure_ascii=False).lower()
    for key in ['"recommendation"', '"action"', '"buy_signal"', '"order"', '"buy"', '"sell"']:
        assert key not in dumped


def test_diag_growth_value_trap():
    """매출 CAGR < -10% → '매출 부진 신호'."""
    income = [_income(revenue=200), _income(revenue=150), _income(revenue=120)]
    result = fr.compute_ratio_analysis(income, [], [], {})
    diag = result["axes"]["growth"]["diagnosis"]
    assert "매출 부진" in diag or "성장성" in diag


# ═══════════════════ overall / 등급 경계 (§D-4) ═══════════════════

def test_overall_average_of_valid_axes():
    """overall = 산출 축 평균. 일부 축 N/A 시 나머지 평균."""
    income = [_income(revenue=100, ni=10), _income(revenue=110, ni=12)]
    bs = [_bs(ta=1000, te=100), _bs(ta=1100, te=120)]
    result = fr.compute_ratio_analysis(income, bs, [], {"roe": 12}, sector_tier="bank_holding")
    # activity N/A → overall은 growth/profitability/stability 평균
    valid_scores = [result["axes"][a]["score"] for a in result["axes"]
                    if result["axes"][a]["applicable"] and result["axes"][a]["score"] is not None]
    if valid_scores:
        assert abs(result["overall_score"] - sum(valid_scores) / len(valid_scores)) < 0.1


def test_grade_boundaries():
    """등급 경계: score→grade 매핑 헬퍼 검증."""
    assert fr._score_to_grade(90) == "우수"
    assert fr._score_to_grade(75) == "양호"
    assert fr._score_to_grade(60) == "보통"
    assert fr._score_to_grade(40) == "주의"
    assert fr._score_to_grade(20) == "위험"
    assert fr._score_to_grade(None) == "N/A"

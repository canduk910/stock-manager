"""구루 투자 공식 모듈 — Greenblatt Magic Formula / Neff Ratio / 서준식 기대수익률.

safety_grade.py(7점 28점)와 별도 운영: 구루 패널 12점 = 3공식 × 4점.

도메인 에이전트 스펙 출처:
- value-screener.md → 구루 프리셋/필터/정규화
- margin-analyst.md → 임계값/등급/재무건전성 연계
- macro-sentinel.md → 체제별 파라미터 차등

사용처:
- routers/screener.py → _enrich_guru() 에서 호출
- pipeline_service.py → (향후) 구루 점수 기반 추천 확장
"""

from __future__ import annotations

from typing import Optional


# ── 업종 제외 ────────────────────────────────────────────────────
# Greenblatt 원서 명시: 금융, 유틸리티 제외. 바이오 추가(적자 다수).
GREENBLATT_EXCLUDED_SECTORS = frozenset({
    "금융", "은행", "보험", "증권", "유틸리티", "전기가스", "바이오",
})


# ── Greenblatt Magic Formula ─────────────────────────────────────

def calc_greenblatt(
    operating_income: Optional[int],
    current_assets: Optional[int],
    current_liabilities: Optional[int],
    ppe: Optional[int],
    mktcap: Optional[int],
    total_liabilities: Optional[int],
    cash_and_equiv: Optional[int],
) -> dict:
    """Greenblatt Magic Formula: ROIC + Earnings Yield.

    ROIC = EBIT / Invested Capital
      - EBIT ≈ 영업이익 (한국 GAAP)
      - Invested Capital = 순운전자본(유동자산-유동부채) + 순고정자산(PPE)

    EY (Earnings Yield) = EBIT / EV
      - EV = 시총 + 총부채 - 현금성자산

    Returns:
        {roic, earnings_yield, roic_score(1~4), ey_score(1~4),
         total_score(2~8), calculable}
    """
    result = {
        "roic": None, "earnings_yield": None,
        "roic_score": 1, "ey_score": 1,
        "total_score": 2, "calculable": False,
    }

    if operating_income is None or mktcap is None or mktcap <= 0:
        return result

    # ROIC
    nwc = (current_assets or 0) - (current_liabilities or 0)
    nfa = ppe or 0
    invested_capital = nwc + nfa
    roic = None
    if invested_capital > 0:
        roic = round(operating_income / invested_capital * 100, 2)

    # EV & Earnings Yield
    ev = mktcap + (total_liabilities or 0) - (cash_and_equiv or 0)
    ey = None
    if ev > 0:
        ey = round(operating_income / ev * 100, 2)

    roic_score = _score_roic(roic)
    ey_score = _score_ey(ey)

    return {
        "roic": roic,
        "earnings_yield": ey,
        "roic_score": roic_score,
        "ey_score": ey_score,
        "total_score": roic_score + ey_score,
        "calculable": roic is not None or ey is not None,
    }


def _score_roic(roic: Optional[float]) -> int:
    if roic is None:
        return 1
    if roic > 25:
        return 4
    if roic > 15:
        return 3
    if roic > 8:
        return 2
    return 1


def _score_ey(ey: Optional[float]) -> int:
    if ey is None:
        return 1
    if ey > 15:
        return 4
    if ey > 10:
        return 3
    if ey > 5:
        return 2
    return 1


# ── Neff Total Return Ratio ──────────────────────────────────────

def calc_neff(
    eps_values: list[Optional[int]],
    dividend_yield: Optional[float],
    per: Optional[float],
) -> dict:
    """John Neff Total Return Ratio.

    Neff Ratio = (EPS CAGR 3년% + 배당수익률%) / PER

    Args:
        eps_values: 과거→최신순 EPS 배열 (최소 2개, 양수만 유효)
        dividend_yield: 배당수익률 (%, 예: 3.5)
        per: PER (<=0 또는 >40이면 적용 불가)

    Returns:
        {eps_cagr, neff_ratio, neff_score(1~4), calculable}
    """
    result = {"eps_cagr": None, "neff_ratio": None, "neff_score": 1, "calculable": False}

    if per is None or per <= 0 or per > 40:
        return result

    valid_eps = [e for e in (eps_values or []) if e is not None and e > 0]
    if len(valid_eps) < 2:
        return result

    oldest, latest = valid_eps[0], valid_eps[-1]
    years = len(valid_eps) - 1

    try:
        eps_cagr = ((latest / oldest) ** (1 / years) - 1) * 100
    except (ValueError, ZeroDivisionError, OverflowError):
        return result

    dy = dividend_yield or 0.0
    neff_ratio = (eps_cagr + dy) / per

    return {
        "eps_cagr": round(eps_cagr, 2),
        "neff_ratio": round(neff_ratio, 3),
        "neff_score": _score_neff(neff_ratio),
        "calculable": True,
    }


def _score_neff(ratio: Optional[float]) -> int:
    if ratio is None:
        return 1
    if ratio > 2.5:
        return 4
    if ratio > 1.5:
        return 3
    if ratio > 0.8:
        return 2
    return 1


# ── 서준식 기대수익률 ────────────────────────────────────────────

def calc_seo_expected_return(
    roe: Optional[float],
    pbr: Optional[float],
    per: Optional[float] = None,
    dividend_yield: Optional[float] = None,
) -> dict:
    """서준식 기대수익률.

    기본: Expected Return = ROE / PBR (%)
    변형(fallback): (1/PER × 100) + 배당수익률

    Returns:
        {expected_return, method("roe_pbr"|"per_dividend"|None),
         seo_score(1~4), calculable}
    """
    result = {"expected_return": None, "method": None, "seo_score": 1, "calculable": False}

    # 기본 공식: ROE / PBR
    if roe is not None and pbr is not None and pbr > 0:
        expected = roe / pbr
        return {
            "expected_return": round(expected, 2),
            "method": "roe_pbr",
            "seo_score": _score_seo(expected),
            "calculable": True,
        }

    # 변형: (1/PER × 100) + 배당수익률
    if per is not None and per > 0:
        expected = (1 / per * 100) + (dividend_yield or 0)
        return {
            "expected_return": round(expected, 2),
            "method": "per_dividend",
            "seo_score": _score_seo(expected),
            "calculable": True,
        }

    return result


def _score_seo(er: Optional[float]) -> int:
    if er is None:
        return 1
    if er > 12:
        return 4
    if er > 8:
        return 3
    if er > 5:
        return 2
    return 1


# ── Graham NCAV ──────────────────────────────────────────────────

def calc_graham_ncav(
    current_assets: Optional[int],
    total_liabilities: Optional[int],
    mktcap: Optional[int],
) -> dict:
    """Graham NCAV (순유동자산가치).

    NCAV = 유동자산 - 총부채
    ncav_ratio = NCAV / 시총 (>= 1.5이면 Graham 원서 매수조건 충족)

    Returns:
        {ncav, ncav_ratio, ncav_score(1~4), calculable}
    """
    result = {"ncav": None, "ncav_ratio": None, "ncav_score": 1, "calculable": False}

    if current_assets is None or total_liabilities is None:
        return result
    if not mktcap or mktcap <= 0:
        return result

    ncav = current_assets - total_liabilities
    result["ncav"] = ncav

    if ncav <= 0:
        return result

    ratio = round(ncav / mktcap, 3)
    result["ncav_ratio"] = ratio
    result["ncav_score"] = _score_ncav(ratio)
    result["calculable"] = True
    return result


def _score_ncav(ratio: Optional[float]) -> int:
    if ratio is None:
        return 1
    if ratio >= 1.5:
        return 4
    if ratio >= 1.0:
        return 3
    if ratio >= 0.5:
        return 2
    return 1


# ── Fisher PSR ───────────────────────────────────────────────────

def calc_fisher_psr(
    mktcap: Optional[int],
    revenue: Optional[int],
) -> dict:
    """Ken Fisher PSR (주가매출비율).

    PSR = 시총 / 매출액
    < 0.75 강력매수, 0.75~1.5 관찰, > 1.5 기준초과.

    Returns:
        {psr, psr_score(1~4), calculable}
    """
    result = {"psr": None, "psr_score": 1, "calculable": False}

    if not mktcap or mktcap <= 0 or not revenue or revenue <= 0:
        return result

    psr = round(mktcap / revenue, 3)
    return {
        "psr": psr,
        "psr_score": _score_psr(psr),
        "calculable": True,
    }


def _score_psr(psr: Optional[float]) -> int:
    if psr is None:
        return 1
    if psr < 0.75:
        return 4
    if psr < 1.0:
        return 3
    if psr < 1.5:
        return 2
    return 1


# ── Piotroski F-Score ────────────────────────────────────────────

def calc_piotroski_fscore(
    bs_list: list[dict],
    cf_list: list[dict],
    is_list: list[dict],
) -> dict:
    """Piotroski F-Score (8점 만점, 신주발행 F7 제외).

    수익성(4): ROA>0, 영업CF>0, ROA증가, Accrual(CF>NI)
    재무구조(2): 부채비율감소, 유동비율증가
    영업효율(2): 매출총이익률증가, 총자산회전율증가

    Args:
        bs_list: balance_sheet 연도 배열 (과거→최신, 최소 2개년)
        cf_list: cashflow 연도 배열
        is_list: income_detail 연도 배열

    Returns:
        {fscore(0~8), details(dict), fscore_score(1~4), calculable}
    """
    result = {"fscore": None, "details": {}, "fscore_score": 1, "calculable": False}

    if len(bs_list) < 2 or len(is_list) < 2:
        return result

    cur_bs, prev_bs = bs_list[-1], bs_list[-2]
    cur_is, prev_is = is_list[-1], is_list[-2]
    cur_cf = cf_list[-1] if cf_list else {}

    cur_ta = cur_bs.get("total_assets") or 0
    prev_ta = prev_bs.get("total_assets") or 0
    cur_ni = cur_is.get("net_income") or 0
    prev_ni = prev_is.get("net_income") or 0
    cur_cf_val = cur_cf.get("operating_cf") or 0

    details = {}

    # F1: ROA > 0
    cur_roa = cur_ni / cur_ta if cur_ta > 0 else 0
    details["f1_roa_positive"] = 1 if cur_roa > 0 else 0

    # F2: 영업CF > 0
    details["f2_cfo_positive"] = 1 if cur_cf_val > 0 else 0

    # F3: ROA 증가
    prev_roa = prev_ni / prev_ta if prev_ta > 0 else 0
    details["f3_roa_increasing"] = 1 if cur_roa > prev_roa else 0

    # F4: Accrual (영업CF > 순이익)
    details["f4_accrual"] = 1 if cur_cf_val > cur_ni else 0

    # F5: 부채비율 감소
    cur_dr = cur_bs.get("debt_ratio")
    prev_dr = prev_bs.get("debt_ratio")
    details["f5_leverage_decreasing"] = 1 if (cur_dr is not None and prev_dr is not None and cur_dr < prev_dr) else 0

    # F6: 유동비율 증가
    cur_cr = cur_bs.get("current_ratio")
    prev_cr = prev_bs.get("current_ratio")
    details["f6_liquidity_increasing"] = 1 if (cur_cr is not None and prev_cr is not None and cur_cr > prev_cr) else 0

    # F7: 신주발행 없음 — DART 미제공, 제외

    # F8: 매출총이익률 증가
    cur_rev = cur_is.get("revenue") or 0
    prev_rev = prev_is.get("revenue") or 0
    cur_gp = cur_is.get("gross_profit") or 0
    prev_gp = prev_is.get("gross_profit") or 0
    cur_gm = cur_gp / cur_rev if cur_rev > 0 else 0
    prev_gm = prev_gp / prev_rev if prev_rev > 0 else 0
    details["f8_margin_increasing"] = 1 if cur_gm > prev_gm else 0

    # F9: 총자산회전율 증가
    cur_turnover = cur_rev / cur_ta if cur_ta > 0 else 0
    prev_turnover = prev_rev / prev_ta if prev_ta > 0 else 0
    details["f9_turnover_increasing"] = 1 if cur_turnover > prev_turnover else 0

    fscore = sum(details.values())

    return {
        "fscore": fscore,
        "details": details,
        "fscore_score": _score_fscore(fscore),
        "calculable": True,
    }


def _score_fscore(fscore: Optional[int]) -> int:
    if fscore is None:
        return 1
    if fscore >= 7:
        return 4
    if fscore >= 5:
        return 3
    if fscore >= 4:
        return 2
    return 1


# ── 구루 패널 통합 점수 ──────────────────────────────────────────

def calc_guru_panel(
    greenblatt: Optional[dict],
    neff: Optional[dict],
    seo: Optional[dict],
    ncav: Optional[dict] = None,
    fisher: Optional[dict] = None,
    piotroski: Optional[dict] = None,
) -> dict:
    """6개 구루 공식 통합 패널 (24점 만점).

    Greenblatt total_score(2~8)를 4점으로 정규화: min(4, round(score/2)).
    가용 공식만으로 비율 환산.

    Returns:
        {total_score(0~24), max_possible, normalized_score(0~100),
         formulas_available(0~6), greenblatt, neff, seo, ncav, fisher, piotroski}
    """
    total = 0
    max_possible = 0
    available = 0

    if greenblatt and greenblatt.get("calculable"):
        gb_normalized = min(4, round(greenblatt["total_score"] / 2))
        total += gb_normalized
        max_possible += 4
        available += 1

    if neff and neff.get("calculable"):
        total += neff["neff_score"]
        max_possible += 4
        available += 1

    if seo and seo.get("calculable"):
        total += seo["seo_score"]
        max_possible += 4
        available += 1

    if ncav and ncav.get("calculable"):
        total += ncav["ncav_score"]
        max_possible += 4
        available += 1

    if fisher and fisher.get("calculable"):
        total += fisher["psr_score"]
        max_possible += 4
        available += 1

    if piotroski and piotroski.get("calculable"):
        total += piotroski["fscore_score"]
        max_possible += 4
        available += 1

    normalized = round(total / max_possible * 100, 1) if max_possible > 0 else 0

    return {
        "total_score": total,
        "max_possible": max_possible,
        "normalized_score": normalized,
        "formulas_available": available,
        "greenblatt": greenblatt,
        "neff": neff,
        "seo": seo,
        "ncav": ncav,
        "fisher": fisher,
        "piotroski": piotroski,
    }


# ── Value Trap 경고 ───────────────────────────────────────────────

def check_value_trap(
    per: Optional[float],
    pbr: Optional[float],
    roe: Optional[float],
    revenue_cagr: Optional[float],
    fcf_years_positive: Optional[int],
    debt_ratio: Optional[float],
    fscore: Optional[int] = None,
    psr: Optional[float] = None,
) -> list[str]:
    """Value Trap 경고 규칙 7개. 해당 시 경고 문자열 리스트 반환."""
    warnings = []
    if pbr is not None and pbr < 0.5 and roe is not None and roe < 3:
        warnings.append("저PBR+저ROE: 자산 가치 함정 가능")
    if per is not None and 0 < per < 5 and revenue_cagr is not None and revenue_cagr < -5:
        warnings.append("저PER+매출역성장: 구조적 쇠퇴 가능")
    if fcf_years_positive is not None and fcf_years_positive == 0:
        warnings.append("FCF 3년 연속 적자: 현금 창출 불능")
    if debt_ratio is not None and debt_ratio > 200:
        warnings.append("부채비율 200%+: 재무 위험")
    if pbr is not None and pbr < 0.7 and debt_ratio is not None and debt_ratio > 150:
        warnings.append("저PBR+고부채: 부실 기업 가능")
    if fscore is not None and fscore <= 2:
        warnings.append("F-Score 극저: 재무건전성 심각 취약")
    if psr is not None and psr < 0.5 and revenue_cagr is not None and revenue_cagr < -10:
        warnings.append("극저PSR+매출급감: 시장이 매출 소멸 반영 중")
    return warnings


# ── 체제별 구루 파라미터 ─────────────────────────────────────────

REGIME_GURU_PARAMS: dict[str, dict] = {
    "accumulation": {
        "greenblatt_roic_min": 8, "greenblatt_ey_min": 5,
        "neff_ratio_min": 0.5, "seo_return_min": 5,
        "ncav_ratio_min": 0.5, "psr_max": 1.5, "fscore_min": 4,
        "description": "관대한 기준 — 축적기 적극 매수",
    },
    "selective": {
        "greenblatt_roic_min": 12, "greenblatt_ey_min": 8,
        "neff_ratio_min": 0.8, "seo_return_min": 8,
        "ncav_ratio_min": 0.8, "psr_max": 1.0, "fscore_min": 5,
        "description": "표준 기준 — 선별적 매수",
    },
    "cautious": {
        "greenblatt_roic_min": 18, "greenblatt_ey_min": 12,
        "neff_ratio_min": 1.5, "seo_return_min": 10,
        "ncav_ratio_min": 1.0, "psr_max": 0.75, "fscore_min": 7,
        "description": "엄격한 기준 — 최우량주만 편입",
    },
    "defensive": {
        "greenblatt_roic_min": 999, "greenblatt_ey_min": 999,
        "neff_ratio_min": 999, "seo_return_min": 999,
        "ncav_ratio_min": 999, "psr_max": 0, "fscore_min": 999,
        "description": "진입 금지 — 현금 보존",
    },
}

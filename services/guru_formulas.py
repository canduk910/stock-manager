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


# ── 구루 패널 통합 점수 ──────────────────────────────────────────

def calc_guru_panel(
    greenblatt: Optional[dict],
    neff: Optional[dict],
    seo: Optional[dict],
) -> dict:
    """3개 구루 공식 통합 패널 (12점 만점).

    Greenblatt total_score(2~8)를 4점으로 정규화: min(4, round(score/2)).
    가용 공식만으로 비율 환산.

    Returns:
        {total_score(0~12), max_possible, normalized_score(0~100),
         formulas_available(0~3), greenblatt, neff, seo}
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

    normalized = round(total / max_possible * 100, 1) if max_possible > 0 else 0

    return {
        "total_score": total,
        "max_possible": max_possible,
        "normalized_score": normalized,
        "formulas_available": available,
        "greenblatt": greenblatt,
        "neff": neff,
        "seo": seo,
    }


# ── Value Trap 경고 ───────────────────────────────────────────────

def check_value_trap(
    per: Optional[float],
    pbr: Optional[float],
    roe: Optional[float],
    revenue_cagr: Optional[float],
    fcf_years_positive: Optional[int],
    debt_ratio: Optional[float],
) -> list[str]:
    """Value Trap 경고 규칙 5개. 해당 시 경고 문자열 리스트 반환."""
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
    return warnings


# ── 체제별 구루 파라미터 ─────────────────────────────────────────

REGIME_GURU_PARAMS: dict[str, dict] = {
    "accumulation": {
        "greenblatt_roic_min": 8,
        "greenblatt_ey_min": 5,
        "neff_ratio_min": 0.5,
        "seo_return_min": 5,
        "description": "관대한 기준 — 축적기 적극 매수",
    },
    "selective": {
        "greenblatt_roic_min": 12,
        "greenblatt_ey_min": 8,
        "neff_ratio_min": 0.8,
        "seo_return_min": 8,
        "description": "표준 기준 — 선별적 매수",
    },
    "cautious": {
        "greenblatt_roic_min": 18,
        "greenblatt_ey_min": 12,
        "neff_ratio_min": 1.5,
        "seo_return_min": 10,
        "description": "엄격한 기준 — 최우량주만 편입",
    },
    "defensive": {
        "greenblatt_roic_min": 999,
        "greenblatt_ey_min": 999,
        "neff_ratio_min": 999,
        "seo_return_min": 999,
        "description": "진입 금지 — 현금 보존",
    },
}

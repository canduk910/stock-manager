"""7점 등급/복합점수/체제정합성/포지션 사이징 공유 로직.

3중 일관성 원칙:
  System Prompt 문자열(advisory_service._build_system_prompt)
  = safety_grade.py 코드 (이 파일의 임계값)
  = Pydantic 타입(schemas/advisory_report_v2.py의 필드 범위)
이 3곳의 임계값이 불일치하면 GPT 등급과 사전 계산 등급이 괴리되므로,
변경 시 반드시 3곳을 동시에 수정해야 한다.

도메인 에이전트 스펙 출처:
- margin-analyst.md → 7점 등급 체계 (7지표 × 4점 = 28점)
- value-screener.md → 복합 점수 공식 (PER/PBR/ROE/배당 가중합)
- order-advisor.md  → 등급별 포지션 사이징 + 손절폭

사용처:
- advisory_service.py → _build_prompt에서 사전 계산값 삽입
- pipeline_service.py → _calc_safety_grade에서 위임 호출
- portfolio_advisor_service.py → 체제 정합성 점수 계산

주요 함수:
- compute_grade_7point(metrics, bs, cf, income, valuation_stats) → {score, grade, details, valid_entry}
- compute_composite_score(metrics) → 0~100 float
- compute_regime_alignment(regime, grade_score, fcf_trend, stock_pct) → 0~100 float
- compute_position_size(grade, regime_single_cap_pct, total_portfolio, cash_available, entry_price) → dict
"""

from __future__ import annotations

from typing import Optional


# ── 등급별 팩터/손절폭 (order-advisor.md) ────────────────────────────────
# GRADE_FACTOR: 등급에 따른 포지션 수량 조절 배수
# 예: selective 체제 종목당 한도 4%일 때 B+ 등급 → 4% × 0.75 = 3.0%
# A=1.0(100%): 강력매수 등급이므로 한도를 최대로 활용
# B+=0.75(75%): 매수 등급이지만 소폭 감액 (리스크 관리)
# B=0.50(50%): 조건부 등급이므로 반으로 축소
# C/D=0: 진입 금지 (매수 불가 등급)
GRADE_FACTOR = {"A": 1.0, "B+": 0.75, "B": 0.5, "C": 0.0, "D": 0.0}

# 등급별 손절폭 — 등급이 높을수록 좁은 손절 (확신이 높으므로 빠르게 손절)
# A=-8%: 강력매수 종목이 8% 하락하면 전제가 틀린 것 → 빠른 손절
# B+=-10%: 매수 종목에 약간 더 여유
# B=-12%: 조건부 종목에 최대 여유
# C/D=None: 진입 자체를 금지
GRADE_STOP_LOSS_PCT = {
    "A": 0.08,    # -8%
    "B+": 0.10,   # -10%
    "B": 0.12,    # -12%
    "C": None,    # 진입 금지
    "D": None,    # 진입 금지
}


# ── 7점 등급 (margin-analyst.md 스펙) ───────────────────────────────────
# 7개 지표를 각 4점 만점으로 평가하여 합산 (최대 28점)
#
# 임계값 표 (ASCII):
# ┌────┬──────────────────┬───────┬──────────┬──────────┬───────┐
# │ #  │ 지표             │ 4점   │ 3점      │ 2점      │ 1점   │
# ├────┼──────────────────┼───────┼──────────┼──────────┼───────┤
# │ 1  │ Graham 할인율    │ >40%  │ 20-40%   │ 0-20%    │ ≤0%   │
# │ 2  │ PER vs 5년평균   │ <-30% │ -30~-10% │ -10~+10% │ >+10% │
# │ 3  │ PBR 절대값       │ <0.7  │ 0.7-1.0  │ 1.0-1.5  │ >1.5  │
# │ 4  │ 부채비율         │ <50%  │ 50-100%  │ 100-200% │ >200% │
# │ 5  │ 유동비율         │ >2.0  │ 1.5-2.0  │ 1.0-1.5  │ <1.0  │
# │ 6  │ FCF 양수 연수    │ 3년   │ 2년      │ 1년      │ 0년   │
# │ 7  │ 매출 CAGR(3년)   │ >10%  │ 5-10%    │ 0-5%     │ <0%   │
# └────┴──────────────────┴───────┴──────────┴──────────┴───────┘
#
# 등급 컷오프: A=24-28 / B+=20-23 / B=16-19 / C=12-15 / D=<12

def _score_discount(discount: Optional[float]) -> int:
    """Graham 할인율 점수. >40=4 / 20-40=3 / 0-20=2 / ≤0=1.

    Graham Number = sqrt(22.5 × EPS × BPS) 대비 현재가의 할인 정도.
    할인율이 높을수록 내재가치 대비 저평가 → 높은 점수.
    """
    if discount is None:
        return 1
    if discount > 40:
        return 4
    if discount > 20:
        return 3
    if discount > 0:
        return 2
    return 1


def _score_per_vs_avg(per: Optional[float], per_avg: Optional[float]) -> int:
    """PER vs 5년 평균 편차%. <-30=4 / -30~-10=3 / -10~+10=2 / >+10=1.

    현재 PER이 5년 평균 대비 크게 낮으면 역사적 저평가 구간 → 높은 점수.
    데이터 없으면 중립 2점으로 처리하여 등급에 큰 영향을 주지 않도록 한다.
    """
    if per is None or per_avg is None or per_avg <= 0:
        return 2  # 데이터 없으면 중립
    diff_pct = (per - per_avg) / per_avg * 100
    if diff_pct < -30:
        return 4
    if diff_pct < -10:
        return 3
    if diff_pct < 10:
        return 2
    return 1


def _score_pbr(pbr: Optional[float]) -> int:
    """PBR 절대값. <0.7=4 / 0.7-1.0=3 / 1.0-1.5=2 / >1.5=1.

    PBR < 1.0은 시가총액이 순자산 가치보다 낮다는 의미 → 자산 대비 저평가.
    0.7 미만은 극단적 저평가 또는 구조적 문제(value trap 가능) → 최고점 부여하되
    다른 지표(FCF, 부채비율)와 교차 검증 필요.
    """
    if pbr is None:
        return 2
    if pbr < 0.7:
        return 4
    if pbr < 1.0:
        return 3
    if pbr < 1.5:
        return 2
    return 1


def _score_debt_ratio(debt_ratio: Optional[float]) -> int:
    """부채비율. <50=4 / 50-100=3 / 100-200=2 / >200=1.

    부채비율 = 총부채 / 자기자본 × 100.
    50% 미만은 재무적으로 매우 안정적, 200% 초과는 과도한 레버리지 → 위험.
    """
    if debt_ratio is None:
        return 2
    if debt_ratio < 50:
        return 4
    if debt_ratio < 100:
        return 3
    if debt_ratio < 200:
        return 2
    return 1


def _score_current_ratio(current_ratio: Optional[float]) -> int:
    """유동비율. >2.0=4 / 1.5-2.0=3 / 1.0-1.5=2 / <1.0=1.

    단위 주의: 유동비율은 보통 %(150) 또는 배수(1.5)로 표현. 양쪽 지원.
    """
    if current_ratio is None:
        return 2
    # %로 표현된 경우 (예: 150) → 배수로 환산
    v = current_ratio / 100 if current_ratio > 10 else current_ratio
    if v > 2.0:
        return 4
    if v > 1.5:
        return 3
    if v > 1.0:
        return 2
    return 1


def _score_fcf_trend(fcf_years_positive: int) -> int:
    """FCF 양수 연수. 3년=4 / 2년=3 / 1년=2 / 0년=1.

    FCF(Free Cash Flow) = 영업현금흐름 - 자본적 지출(CAPEX).
    최근 3년 연속 FCF 양수이면 자체 현금 창출 능력이 검증된 것으로 판단.
    연속이 아닌 경우에도 양수 연수만 카운트한다 (_count_fcf_years_positive에서 break).
    """
    if fcf_years_positive >= 3:
        return 4
    if fcf_years_positive >= 2:
        return 3
    if fcf_years_positive >= 1:
        return 2
    return 1


def _score_revenue_cagr(revenue_cagr: Optional[float]) -> int:
    """매출 CAGR. >10=4 / 5-10=3 / 0-5=2 / <0=1.

    CAGR(Compound Annual Growth Rate) = 연평균 복합 성장률.
    10% 초과는 고성장, 0% 미만은 매출 감소(구조적 쇠퇴 또는 경기 민감) → 위험.
    """
    if revenue_cagr is None:
        return 2
    if revenue_cagr > 10:
        return 4
    if revenue_cagr > 5:
        return 3
    if revenue_cagr > 0:
        return 2
    return 1


def _calc_discount(graham_number: Optional[float], current_price: Optional[float]) -> Optional[float]:
    """Graham Number 대비 현재가 할인율% = (GN - price) / price × 100."""
    if graham_number is None or current_price is None or current_price <= 0:
        return None
    return round((graham_number - current_price) / current_price * 100, 1)


def _count_fcf_years_positive(cashflow: list[dict]) -> int:
    """cashflow 리스트 최신 3년 FCF 양수 연속 연수.

    최신 연도부터 역순으로 탐색하며, 첫 음수 FCF 발견 시 중단(break).
    따라서 "연속" 양수 연수를 반환한다 (중간에 음수가 있으면 그 이후만 카운트).
    """
    if not cashflow:
        return 0
    years_positive = 0
    for entry in reversed(cashflow[-3:]):
        op_cf = entry.get("operating_cf") or entry.get("operating_cashflow") or entry.get("op_cashflow") or 0
        # FCF가 직접 있으면 우선 사용
        fcf = entry.get("free_cf") or entry.get("fcf")
        if fcf is None:
            capex = abs(entry.get("capex") or entry.get("capital_expenditure") or 0)
            fcf = (op_cf or 0) - capex
        if fcf and fcf > 0:
            years_positive += 1
        else:
            break
    return years_positive


def _calc_revenue_cagr(income_stmt: list[dict]) -> Optional[float]:
    """손익계산서 매출 CAGR (3년 기준, 최소 2년).

    USD/KRW 단위 무관 — 비율 계산이므로 단위 일관되면 정확함 (MarginAnalyst 자문 Phase 2-4).
    """
    if not income_stmt or len(income_stmt) < 2:
        return None
    first_rev = income_stmt[0].get("revenue")
    last_rev = income_stmt[-1].get("revenue")
    years = len(income_stmt) - 1
    if not first_rev or not last_rev or first_rev <= 0 or years <= 0:
        return None
    try:
        return round(((last_rev / first_rev) ** (1 / years) - 1) * 100, 1)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def compute_grade_7point(
    metrics: dict,
    balance_sheet: list[dict],
    cashflow: list[dict],
    income_stmt: list[dict],
    valuation_stats: Optional[dict] = None,
    graham_number: Optional[float] = None,
    current_price: Optional[float] = None,
) -> dict:
    """7개 지표 기반 종합 등급 (28점 만점). pipeline_service._calc_safety_grade 이전/일반화.

    Args:
        metrics: {per, pbr, roe, debt_to_equity or debt_ratio, current_ratio, ...}
        balance_sheet: [{year, total_assets, total_equity, debt_ratio, current_ratio, ...}]
        cashflow: [{year, operating_cf, free_cf, capex, ...}]
        income_stmt: [{year, revenue, operating_income, net_income, ...}]
        valuation_stats: {per_avg_5y, ...} (Phase 2-2). 없으면 PER vs 평균 점수 중립(2점).
        graham_number: Graham Number (없으면 할인율 None → 1점)
        current_price: 현재가

    Returns:
        {
            score: int 0~28,
            grade: "A" | "B+" | "B" | "C" | "D",
            grade_factor: float (A=1.0, B+=0.75, B=0.5, C/D=0),
            valid_entry: bool (C/D는 False),
            details: {
                discount: {value, points},
                per_vs_avg: {value, avg, points},
                pbr: {value, points},
                debt_ratio: {value, points},
                current_ratio: {value, points},
                fcf_trend: {years_positive, points},
                revenue_cagr: {value, points},
            },
        }
    """
    # 1. Graham 할인율
    discount = _calc_discount(graham_number, current_price)
    pts_discount = _score_discount(discount)

    # 2. PER vs 5년 평균
    per = metrics.get("per") if metrics else None
    per_avg = None
    if valuation_stats:
        per_avg = valuation_stats.get("per_avg_5y")
    pts_per = _score_per_vs_avg(per, per_avg)

    # 3. PBR 절대
    pbr = metrics.get("pbr") if metrics else None
    pts_pbr = _score_pbr(pbr)

    # 4. 부채비율 (BS 최신 또는 metrics)
    debt_ratio = None
    if balance_sheet:
        latest = balance_sheet[-1]
        debt_ratio = latest.get("debt_ratio")
        if debt_ratio is None:
            total_debt = latest.get("total_debt") or latest.get("total_liabilities")
            total_equity = latest.get("total_equity") or latest.get("stockholders_equity")
            if total_debt and total_equity and total_equity > 0:
                debt_ratio = round(total_debt / total_equity * 100, 1)
    if debt_ratio is None and metrics:
        debt_ratio = metrics.get("debt_to_equity") or metrics.get("debt_ratio")
    pts_debt = _score_debt_ratio(debt_ratio)

    # 5. 유동비율
    current_ratio = None
    if balance_sheet:
        latest = balance_sheet[-1]
        current_ratio = latest.get("current_ratio")
        if current_ratio is None:
            ca = latest.get("current_assets")
            cl = latest.get("current_liabilities")
            if ca and cl and cl > 0:
                current_ratio = round(ca / cl, 2)
    if current_ratio is None and metrics:
        current_ratio = metrics.get("current_ratio")
    pts_current = _score_current_ratio(current_ratio)

    # 6. FCF 양수 연수
    fcf_years = _count_fcf_years_positive(cashflow)
    pts_fcf = _score_fcf_trend(fcf_years)

    # 7. 매출 CAGR
    revenue_cagr = _calc_revenue_cagr(income_stmt)
    pts_cagr = _score_revenue_cagr(revenue_cagr)

    score = pts_discount + pts_per + pts_pbr + pts_debt + pts_current + pts_fcf + pts_cagr

    # 등급 컷오프 (margin-analyst.md)
    if score >= 24:
        grade = "A"
    elif score >= 20:
        grade = "B+"
    elif score >= 16:
        grade = "B"
    elif score >= 12:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": score,
        "grade": grade,
        "grade_factor": GRADE_FACTOR.get(grade, 0.0),
        "valid_entry": grade in ("A", "B+", "B"),
        "details": {
            "discount": {"value": discount, "points": pts_discount},
            "per_vs_avg": {"value": per, "avg": per_avg, "points": pts_per},
            "pbr": {"value": pbr, "points": pts_pbr},
            "debt_ratio": {"value": debt_ratio, "points": pts_debt},
            "current_ratio": {"value": current_ratio, "points": pts_current},
            "fcf_trend": {"years_positive": fcf_years, "points": pts_fcf},
            "revenue_cagr": {"value": revenue_cagr, "points": pts_cagr},
        },
    }


# ── 복합 점수 (value-screener.md ValueScreener 공식) ────────────────────

def compute_composite_score(metrics: dict) -> Optional[float]:
    """ValueScreener 복합 점수 0~100.

    공식: (1/PER × 0.3 + 1/PBR × 0.3 + ROE/100 × 0.25 + dividend_yield/100 × 0.15) × 100

    가중치 근거 (ValueScreener 에이전트 스펙):
    - PER 역수(0.3) + PBR 역수(0.3) = 밸류에이션 60% — 저평가 종목 선호
    - ROE(0.25) = 수익성 25% — 자기자본 수익률이 높은 기업 선호
    - 배당수익률(0.15) = 주주환원 15% — 배당 지급 기업 가산

    정상적인 저평가+고ROE 종목의 raw값이 0.5~1.0 범위이므로 ×100하면 50~100 스케일.
    PER/PBR ≤ 0 또는 None → 해당 항목 0점 처리 (전체 점수는 여전히 계산).
    배당수익률은 %(3.5) 또는 소수점(0.035) 모두 지원 (> 1이면 %, else 소수점으로 간주).
    """
    if not metrics:
        return None

    per = metrics.get("per")
    pbr = metrics.get("pbr")
    roe = metrics.get("roe")
    dy = metrics.get("dividend_yield")

    # PER 역수
    per_inv = 0.0
    if per and per > 0:
        per_inv = 1 / per

    pbr_inv = 0.0
    if pbr and pbr > 0:
        pbr_inv = 1 / pbr

    roe_term = 0.0
    if roe is not None:
        roe_term = roe / 100

    dy_term = 0.0
    if dy is not None:
        # %(3.5) 또는 소수점(0.035) 판별 — 1 이상이면 %
        dy_norm = dy / 100 if abs(dy) > 1 else dy
        dy_term = dy_norm

    raw = (per_inv * 0.3) + (pbr_inv * 0.3) + (roe_term * 0.25) + (dy_term * 0.15)
    # 0~100 스케일: 정상적인 저평가 고ROE 종목이 ~0.5~1.0 수준. ×100 후 min(100) 적용
    score = round(raw * 100, 1)
    return min(max(score, 0.0), 100.0)


# ── 체제 정합성 ─────────────────────────────────────────────────────────
# 체제가 엄격할수록 높은 등급을 요구하여 부적격 종목 편입을 방지한다.

# 체제별 기대 등급 점수 (score 중심값)
# accumulation/selective: B+(20점) 이상이면 체제에 적합
# cautious: A(24점) 이상을 요구 — 신중한 체제에서는 우량주만 편입
# defensive: A 최대(28점)를 요구 — 사실상 어떤 종목도 진입 불가 (현금 보존)
_REGIME_EXPECTED_GRADE = {
    "accumulation": 20,  # B+ 기대
    "selective": 20,     # B+ 기대
    "cautious": 24,      # A 기대 (엄격)
    "defensive": 28,     # A만 허용 (사실상 진입 안 함)
}

# 체제별 권고 주식 비중 (stock_max, 공용 macro_regime.REGIME_PARAMS 참조)
_REGIME_EXPECTED_STOCK_PCT = {
    "accumulation": 75,
    "selective": 65,
    "cautious": 50,
    "defensive": 25,
}


def compute_regime_alignment(
    regime: str,
    grade_score: Optional[int],
    fcf_years_positive: Optional[int],
    stock_pct: Optional[float] = None,
) -> float:
    """체제 정합성 점수 0~100.

    종목(또는 포트폴리오)이 현재 시장 체제에 얼마나 적합한지를 정량화한다.

    구성 (3항목 가중합):
    - 등급 정합 (40%): 체제별 기대 점수 대비 실제 점수.
      기대치 초과 → 100, 최저(D=8점)까지 선형 감소 → 0
    - FCF 정합 (30%): 현금 창출 안정성.
      3년 연속 양수=100, 2년=75, 1년=50, 0년=25
    - 주식비중 정합 (30%): 체제 권고 주식 비중과의 오차.
      ±5%p 이내=100, ±20%p 초과=0, 그 사이 선형 감소
      stock_pct가 None이면 등급+FCF 2항목만 사용 (50/50 가중)

    활용: advisory_service 프롬프트에 참고값으로 삽입,
    portfolio_advisor_service에서 포트폴리오 차원 정합성 판단에 사용.
    """
    # 1. 등급 정합
    expected_score = _REGIME_EXPECTED_GRADE.get(regime, 20)
    if grade_score is None:
        grade_align = 50.0
    else:
        # 기대치를 초과하면 100, 기대치 - 12(=최저 D)이면 0
        # D=8(최저), expected=20(B+) 이면 범위 12
        diff = grade_score - expected_score
        if diff >= 0:
            grade_align = 100.0
        else:
            grade_align = max(0.0, 100.0 + diff * 100.0 / 12)  # -12 → 0

    # 2. FCF 정합
    if fcf_years_positive is None:
        fcf_align = 50.0
    elif fcf_years_positive >= 3:
        fcf_align = 100.0
    elif fcf_years_positive >= 2:
        fcf_align = 75.0
    elif fcf_years_positive >= 1:
        fcf_align = 50.0
    else:
        fcf_align = 25.0

    # 3. 주식비중 정합
    if stock_pct is None:
        # 2항목만 사용 (등급+FCF, 가중치 50/50)
        return round(grade_align * 0.5 + fcf_align * 0.5, 1)

    expected_stock = _REGIME_EXPECTED_STOCK_PCT.get(regime, 65)
    # 권고치 대비 오차 5%p 이내는 100, 20%p 초과는 0
    stock_diff = abs(stock_pct - expected_stock)
    if stock_diff <= 5:
        stock_align = 100.0
    elif stock_diff >= 20:
        stock_align = 0.0
    else:
        stock_align = max(0.0, 100.0 - (stock_diff - 5) * 100.0 / 15)

    return round(grade_align * 0.4 + fcf_align * 0.3 + stock_align * 0.3, 1)


# ── 포지션 사이징 (order-advisor.md) ────────────────────────────────────
# GRADE_FACTOR × 체제 한도로 최종 투자 비중을 결정한다.
# 예시:
#   selective 체제(single_cap=4%) + B+ 등급(factor=0.75) = 3.0%
#   accumulation 체제(single_cap=5%) + A 등급(factor=1.0) = 5.0%
#   어떤 체제든 C/D 등급(factor=0) = 0% (진입 금지)

def compute_position_size(
    grade: str,
    regime_single_cap_pct: float,
    total_portfolio: float,
    cash_available: float,
    entry_price: float,
) -> dict:
    """등급 × 체제 한도 기반 수량 계산.

    계산 공식:
    target_pct = regime_single_cap_pct × grade_factor / 100
    max_amount = total_portfolio × target_pct
    available = min(max_amount, cash_available)  # 예수금 제한
    qty = floor(available / entry_price)

    C/D 등급 또는 진입가 ≤ 0 → qty=0, recommendation="SKIP".
    qty > 0이면 "ENTER", qty = 0이면 "HOLD" (자금 부족).
    """
    factor = GRADE_FACTOR.get(grade, 0.0)
    if factor == 0 or entry_price <= 0:
        return {
            "qty": 0,
            "amount": 0,
            "position_pct": 0.0,
            "grade_factor": factor,
            "recommendation": "SKIP",
            "reason": "grade_or_price_invalid",
        }

    target_pct = regime_single_cap_pct * factor / 100  # 예: 4% × 0.75 = 0.03
    max_amount = total_portfolio * target_pct
    available = min(max_amount, cash_available)
    raw_qty = int(available // entry_price) if entry_price > 0 else 0

    return {
        "qty": raw_qty,
        "amount": raw_qty * entry_price,
        "position_pct": round(target_pct * 100, 2),
        "grade_factor": factor,
        "recommendation": "ENTER" if raw_qty > 0 else "HOLD",
        "reason": None,
    }


def compute_stop_loss(grade: str, entry_price: float) -> Optional[float]:
    """등급별 손절가. A=-8%, B+=-10%, B=-12%, C/D=None (진입 금지)."""
    pct = GRADE_STOP_LOSS_PCT.get(grade)
    if pct is None or entry_price <= 0:
        return None
    return round(entry_price * (1 - pct), 2)


def compute_risk_reward(entry: Optional[float], stop: Optional[float], target: Optional[float]) -> Optional[float]:
    """리스크보상비율 = (target - entry) / (entry - stop). <2.0이면 매수 보류 권고."""
    if entry is None or stop is None or target is None:
        return None
    if entry <= stop or entry <= 0:
        return None
    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return None
    return round(reward / risk, 2)


__all__ = [
    "GRADE_FACTOR",
    "GRADE_STOP_LOSS_PCT",
    "compute_grade_7point",
    "compute_composite_score",
    "compute_regime_alignment",
    "compute_position_size",
    "compute_stop_loss",
    "compute_risk_reward",
]

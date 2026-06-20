"""4축 재무비율 평가 — 순수 함수 (외부 호출 0).

연세대 정보대학원 〈AI와 신용평가모형〉 "전통적 재무정보 4유형"
(활동성/성장성/수익성/안정성)을 신용평가(부실/위험 신호 탐지) 관점으로 차용.
Graham 보수주의 원칙으로 임계값 보정. 도메인 합의(2026-06-19).

설계 규약 (safety_grade.py 패턴 준수):
- import 부수효과 0 (DB/네트워크/파일 접근 없음).
- 모든 리스트 입력은 오래된순(과거→최신) 정렬. [-1]=최신, [0]=가장 과거.
- 비율 계산 입력 결손(None/분모≤0) → 비율 None (0점 부여하지 않음, 평균에서 제외).
- 회전율 분모 = 기말잔액(latest BS), 추세 = 정규화 선형회귀 기울기(§D-1/§D-2).
- 수익성·안정성 = 절대 임계값, 활동성·성장성 = 자기 시계열 추세(§D-3).
- 축 점수 = mean(유효 비율 점수) × 25. overall = 산출 축(N/A 제외) 평균.
- 금융업(bank_holding/insurance/securities) 분기(§D-5).
- 진단 문구는 서술형(신호/우려/관찰 권고)만. 매매 액션 키 금지(§D-7).

단일 진입점: compute_ratio_analysis(income_stmt, balance_sheet, cashflow,
                                   metrics, sector_tier="general") -> dict
"""

from __future__ import annotations

from typing import Optional

_FINANCIAL_TIERS = ("bank_holding", "insurance", "securities")
_METHOD = "ratio_4axis_v1"


# ════════════════════ 공통 헬퍼 ════════════════════

def _num(v) -> Optional[float]:
    """숫자 변환. None/비숫자/NaN → None."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _ratio(numerator, denominator) -> Optional[float]:
    """분자/분모. 분모 ≤ 0 또는 None → None."""
    n = _num(numerator)
    d = _num(denominator)
    if n is None or d is None or d <= 0:
        return None
    return n / d


def _latest_with_fallback(rows: list, key: str) -> Optional[float]:
    """latest(rows[-1]) 값. None이면 직전 연도 fallback 1회 (절대 임계값용)."""
    if not rows:
        return None
    v = _num((rows[-1] or {}).get(key)) if isinstance(rows[-1], dict) else None
    if v is not None:
        return v
    if len(rows) >= 2 and isinstance(rows[-2], dict):
        return _num(rows[-2].get(key))
    return None


def _normalized_slope_pct(values: list[Optional[float]]) -> Optional[float]:
    """정규화 선형회귀 기울기% = slope / mean(values) × 100 (§D-2).

    - 존재하는 (연도인덱스, 값) 쌍만 사용 (중간 None 제외).
    - 최소 2개 유효점 필요.
    - 정확히 2점이면 단순 변화율 (last-first)/|first|×100 fallback.
    - mean ≤ 0 이면 None (왜곡 방지).
    """
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    if len(pts) < 2:
        return None

    vals = [v for _, v in pts]
    mean = sum(vals) / len(vals)

    # 2점: 단순 변화율
    if len(pts) == 2:
        first = pts[0][1]
        last = pts[1][1]
        if first == 0:
            return None
        return (last - first) / abs(first) * 100

    if mean <= 0:
        return None

    # 최소제곱 회귀 기울기
    n = len(pts)
    xs = [float(i) for i, _ in pts]
    ys = vals
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope / mean * 100


def _cagr_pct(values: list[Optional[float]]) -> Optional[float]:
    """CAGR% = (last/first)^(1/년수) - 1 × 100 (§REQ-SCREEN-01).

    - 존재하는 값만 사용 (first=가장 과거 유효, last=가장 최신 유효).
    - first ≤ 0 → None (음수 기저 CAGR 무의미).
    - 최소 2개 유효점 필요. 년수 = (유효점 수 - 1).
    """
    pts = [v for v in values if v is not None]
    if len(pts) < 2:
        return None
    first = pts[0]
    last = pts[-1]
    years = len(pts) - 1
    if first <= 0 or years <= 0:
        return None
    try:
        return ((last / first) ** (1 / years) - 1) * 100
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


# ════════════════════ 점수 헬퍼 (절대/추세 임계값) ════════════════════

def _score_activity_trend(slope_pct: Optional[float]) -> Optional[int]:
    """활동성 추세: >+10=4 / 0~+10=3 / [-5,0)=2 / <-5=1 (§REQ-MARGIN-02 비대칭 보합)."""
    if slope_pct is None:
        return None
    if slope_pct > 10:
        return 4
    if slope_pct >= 0:
        return 3
    if slope_pct >= -5:
        return 2
    return 1


def _score_growth_cagr(cagr: Optional[float]) -> Optional[int]:
    """성장성 CAGR: >15=4 / 5~15=3 / 0~5=2 / <0=1."""
    if cagr is None:
        return None
    if cagr > 15:
        return 4
    if cagr >= 5:
        return 3
    if cagr >= 0:
        return 2
    return 1


def _score_oi_margin(v: Optional[float]) -> Optional[int]:
    """영업이익률: >15=4 / 8~15=3 / 0~8=2 / <0=1."""
    if v is None:
        return None
    if v > 15:
        return 4
    if v >= 8:
        return 3
    if v >= 0:
        return 2
    return 1


def _score_roe(v: Optional[float]) -> Optional[int]:
    """ROE: >15=4 / 8~15=3 / 0~8=2 / <0=1."""
    if v is None:
        return None
    if v > 15:
        return 4
    if v >= 8:
        return 3
    if v >= 0:
        return 2
    return 1


def _score_roa(v: Optional[float]) -> Optional[int]:
    """ROA: >7=4 / 3~7=3 / 0~3=2 / <0=1."""
    if v is None:
        return None
    if v > 7:
        return 4
    if v >= 3:
        return 3
    if v >= 0:
        return 2
    return 1


def _score_interest_coverage(
    coverage: Optional[float], operating_income: Optional[float],
    interest_expense: Optional[float]
) -> Optional[int]:
    """이자보상비율(배): >5=4 / 3~5=3 / 1~3=2 / <1=1.

    None↔0 구분 (bug_004 도메인 확정 2026-06-19, MarginAnalyst):
    - interest_expense == 0 (실측 무차입) → 영업흑자 4점 / 영업적자 1점 (§REQ-MARGIN-03).
    - interest_expense is None (DART 라벨 변형 파싱 실패: '이자비용계' 등) → None.
      무차입(0)과 구분하여 '무차입 우량 4점'을 부여하지 않는다(Graham "추측으로
      빈칸 안 채움"). 호출부(_compute_profitability)는 BS 차입 잔액이 있으면 더더욱
      파싱 누락이 명백하므로 ie를 None 그대로 전달한다(§D-6 skip).
    """
    ie = _num(interest_expense)
    oi = _num(operating_income)
    if ie is None:
        # 파싱 실패 — 무차입(0)과 구분. 4점 false-positive 차단.
        return None
    if ie == 0:
        # 실측 무차입 우량.
        if oi is not None:
            return 4 if oi > 0 else 1
        return None
    if coverage is None:
        return None
    if coverage > 5:
        return 4
    if coverage >= 3:
        return 3
    if coverage >= 1:
        return 2
    return 1


def _score_debt_ratio(v: Optional[float]) -> Optional[int]:
    """부채비율: <100=4 / 100~150=3 / 150~250=2 / >250=1 (한국 상장사 보정)."""
    if v is None:
        return None
    if v < 100:
        return 4
    if v <= 150:
        return 3
    if v <= 250:
        return 2
    return 1


def _score_equity_ratio_general(v: Optional[float]) -> Optional[int]:
    """자기자본비율(일반): >50=4 / 35~50=3 / 20~35=2 / <20=1."""
    if v is None:
        return None
    if v > 50:
        return 4
    if v >= 35:
        return 3
    if v >= 20:
        return 2
    return 1


def _score_equity_ratio_insurance(v: Optional[float]) -> Optional[int]:
    """보험사 자기자본비율 (K-ICS): >15=4 / 10~15=3 / 5~10=2 / <5=1."""
    if v is None:
        return None
    if v > 15:
        return 4
    if v >= 10:
        return 3
    if v >= 5:
        return 2
    return 1


def _score_equity_ratio_bank(v: Optional[float]) -> Optional[int]:
    """은행지주/증권 자기자본비율 (BIS/NCR 근사): >12=4 / 8~12=3 / 4~8=2 / <4=1."""
    if v is None:
        return None
    if v > 12:
        return 4
    if v >= 8:
        return 3
    if v >= 4:
        return 2
    return 1


def _score_debt_dependency(v: Optional[float]) -> Optional[int]:
    """차입금의존도: <15=4 / 15~30=3 / 30~45=2 / >45=1."""
    if v is None:
        return None
    if v < 15:
        return 4
    if v <= 30:
        return 3
    if v <= 45:
        return 2
    return 1


def _normalize_current_ratio(v: Optional[float]) -> Optional[float]:
    """유동비율 단위 정규화: >10이면 %로 간주(그대로), ≤10이면 배수→×100 (§REQ-MARGIN-04)."""
    if v is None:
        return None
    return v if v > 10 else v * 100


def _score_current_ratio(v_pct: Optional[float]) -> Optional[int]:
    """유동비율(%): >150=4 / 120~150=3 / 100~120=2 / <100=1."""
    if v_pct is None:
        return None
    if v_pct > 150:
        return 4
    if v_pct >= 120:
        return 3
    if v_pct >= 100:
        return 2
    return 1


# ════════════════════ 등급/축 헬퍼 ════════════════════

def _score_to_grade(score: Optional[float]) -> str:
    """점수→등급 (§D-4 5단계). None → N/A."""
    if score is None:
        return "N/A"
    if score >= 85:
        return "우수"
    if score >= 70:
        return "양호"
    if score >= 50:
        return "보통"
    if score >= 30:
        return "주의"
    return "위험"


def _axis_score(ratios: dict) -> Optional[float]:
    """유효 비율 점수 평균 × 25. 유효 0개 → None."""
    pts = [r["points"] for r in ratios.values() if r.get("points") is not None]
    if not pts:
        return None
    return round(sum(pts) / len(pts) * 25, 2)


# ════════════════════ 진단 (REQ-DIAG-01) ════════════════════

# 강의 4유형 라벨 (사용자 확정). 매매 액션 키워드 금지(§D-7).
_DIAG_LOW = {
    "activity": "비효율적 경영 신호",
    "growth": "매출 부진 신호",
    "profitability": "수익성 악화 신호",
    "stability": "자금조달 능력 저하",
}
_DIAG_WEAK_SUFFIX = {
    "activity": "특히 {label} 회전 둔화",
    "growth": "특히 {label} 역성장/정체",
    "profitability": "특히 {label} 부진",
    "stability": "특히 {label} 취약",
}
_AXIS_LABEL_KR = {
    "activity": "활동성",
    "growth": "성장성",
    "profitability": "수익성",
    "stability": "안정성",
}
# 비율 키 → 진단용 한글 라벨
_RATIO_LABEL_KR = {
    "total_asset_turnover": "총자산",
    "receivables_turnover": "매출채권",
    "inventory_turnover": "재고자산",
    "payables_turnover": "매입채무",
    "revenue_growth": "매출액",
    "operating_income_growth": "영업이익",
    "net_income_growth": "순이익",
    "total_asset_growth": "총자산",
    "oi_margin": "영업이익률",
    "interest_coverage": "이자보상비율",
    "roe": "ROE",
    "roa": "ROA",
    "debt_ratio": "부채비율",
    "equity_ratio": "자기자본비율",
    "debt_dependency": "차입금의존도",
    "current_ratio": "유동비율",
}


def _build_diagnosis(axis_key: str, score: Optional[float], ratios: dict,
                     ratio_order: list[str]) -> str:
    """축 진단 문구 생성 (서술형, 매매 명령 금지)."""
    axis_label = _AXIS_LABEL_KR[axis_key]
    if score is None:
        return f"{axis_label} 해당 업종 적용 불가(N/A)"
    if score >= 85:
        return f"{axis_label} 우수"
    if score >= 70:
        return f"{axis_label} 양호"
    if score >= 50:
        return f"{axis_label} 보통 — 관찰 권고"
    # score < 50 → 부실 신호 + 최저 비율 지목 (계산식 표상 첫 비율 우선 동률)
    base = _DIAG_LOW[axis_key]
    weakest_key = None
    weakest_pts = None
    for key in ratio_order:
        r = ratios.get(key)
        if not r or r.get("points") is None:
            continue
        if weakest_pts is None or r["points"] < weakest_pts:
            weakest_pts = r["points"]
            weakest_key = key
    if weakest_key is None:
        return base
    label = _RATIO_LABEL_KR.get(weakest_key, weakest_key)
    suffix = _DIAG_WEAK_SUFFIX[axis_key].format(label=label)
    return f"{base} — {suffix}"


# ════════════════════ 축별 계산 ════════════════════

def _compute_activity(income_stmt, balance_sheet, is_financial) -> dict:
    """활동성 축 (§REQ-MARGIN-02). 금융업은 N/A."""
    ratio_order = ["total_asset_turnover", "receivables_turnover",
                   "inventory_turnover", "payables_turnover"]
    if is_financial:
        return _na_axis("activity", ratio_order,
                        "금융업: 재고/매출원가/매출채권 회전 개념 무의미")

    # 연도별 비율 시계열 산출 (income[year] / balance_sheet[year] 매칭)
    n = min(len(income_stmt), len(balance_sheet))
    specs = {
        "total_asset_turnover": ("revenue", "total_assets"),
        "receivables_turnover": ("revenue", "receivables"),
        "inventory_turnover": ("cogs", "inventories"),
        "payables_turnover": ("cogs", "payables"),
    }
    ratios = {}
    for key, (num_k, den_k) in specs.items():
        series = []
        for i in range(n):
            inc = income_stmt[i] if isinstance(income_stmt[i], dict) else {}
            bs = balance_sheet[i] if isinstance(balance_sheet[i], dict) else {}
            series.append(_ratio(inc.get(num_k), bs.get(den_k)))
        slope = _normalized_slope_pct(series)
        latest_val = next((v for v in reversed(series) if v is not None), None)
        ratios[key] = {
            "value": round(latest_val, 4) if latest_val is not None else None,
            "points": _score_activity_trend(slope),
            "trend_pct": round(slope, 2) if slope is not None else None,
        }
    return _finalize_axis("activity", ratios, ratio_order)


def _compute_growth(income_stmt, balance_sheet, is_financial) -> dict:
    """성장성 축 (§REQ-SCREEN-01). 금융업도 일반과 동일."""
    ratio_order = ["revenue_growth", "operating_income_growth",
                   "net_income_growth", "total_asset_growth"]
    specs_income = {
        "revenue_growth": "revenue",
        "operating_income_growth": "operating_income",
        "net_income_growth": "net_income",
    }
    ratios = {}
    for key, field in specs_income.items():
        series = [_num(r.get(field)) if isinstance(r, dict) else None for r in income_stmt]
        cagr = _cagr_pct(series)
        ratios[key] = {
            "value": round(cagr, 2) if cagr is not None else None,
            "points": _score_growth_cagr(cagr),
            "trend_pct": round(cagr, 2) if cagr is not None else None,
        }
    ta_series = [_num(r.get("total_assets")) if isinstance(r, dict) else None
                 for r in balance_sheet]
    ta_cagr = _cagr_pct(ta_series)
    ratios["total_asset_growth"] = {
        "value": round(ta_cagr, 2) if ta_cagr is not None else None,
        "points": _score_growth_cagr(ta_cagr),
        "trend_pct": round(ta_cagr, 2) if ta_cagr is not None else None,
    }
    return _finalize_axis("growth", ratios, ratio_order)


def _compute_profitability(income_stmt, balance_sheet, metrics, sector_tier) -> dict:
    """수익성 축 (§REQ-MARGIN-03). 금융업은 ROE/ROA만."""
    is_financial = sector_tier in _FINANCIAL_TIERS
    ratio_order = ["oi_margin", "interest_coverage", "roe", "roa"]

    # ROE (metrics 우선, 없으면 latest net_income/total_equity×100 — bug_011 oi_margin 패턴과 일관)
    # ROA = latest net_income / total_assets × 100
    ni = _latest_with_fallback(income_stmt, "net_income")
    ta = _latest_with_fallback(balance_sheet, "total_assets")
    roa_ratio = _ratio(ni, ta)
    roa = roa_ratio * 100 if roa_ratio is not None else None

    roe = _num(metrics.get("roe")) if metrics else None
    if roe is None:
        # ROE 분모 = 자기자본(MarginAnalyst 확정). te ≤ 0(자본잠식)이면 _ratio가 None(분모 보호).
        te_roe = _latest_with_fallback(balance_sheet, "total_equity")
        roe_ratio = _ratio(ni, te_roe)
        roe = roe_ratio * 100 if roe_ratio is not None else None

    ratios = {
        "roe": {"value": round(roe, 2) if roe is not None else None,
                "points": _score_roe(roe), "trend_pct": None},
        "roa": {"value": round(roa, 2) if roa is not None else None,
                "points": _score_roa(roa), "trend_pct": None},
    }

    if not is_financial:
        # 영업이익률: metrics 우선, 없으면 latest operating_income/revenue×100
        oim = _num(metrics.get("oi_margin")) if metrics else None
        if oim is None:
            oi = _latest_with_fallback(income_stmt, "operating_income")
            rev = _latest_with_fallback(income_stmt, "revenue")
            r = _ratio(oi, rev)
            oim = r * 100 if r is not None else None
        # 이자보상비율
        oi_latest = _latest_with_fallback(income_stmt, "operating_income")
        ie_latest = _latest_with_fallback(income_stmt, "interest_expense")
        cov = _ratio(oi_latest, ie_latest) if (ie_latest and ie_latest > 0) else None
        ratios["oi_margin"] = {
            "value": round(oim, 2) if oim is not None else None,
            "points": _score_oi_margin(oim), "trend_pct": None,
        }
        ratios["interest_coverage"] = {
            "value": round(cov, 2) if cov is not None else None,
            "points": _score_interest_coverage(cov, oi_latest, ie_latest),
            "trend_pct": None,
        }

    return _finalize_axis("profitability", ratios, ratio_order)


def _compute_stability(balance_sheet, metrics, sector_tier) -> dict:
    """안정성 축 (§REQ-MARGIN-04). 금융업은 자기자본비율(tier별 임계)만."""
    is_financial = sector_tier in _FINANCIAL_TIERS
    ratio_order = ["debt_ratio", "equity_ratio", "debt_dependency", "current_ratio"]

    ta = _latest_with_fallback(balance_sheet, "total_assets")
    te = _latest_with_fallback(balance_sheet, "total_equity")

    # 자기자본비율 = total_equity / total_assets × 100
    er_ratio = _ratio(te, ta)
    er = er_ratio * 100 if er_ratio is not None else None
    if sector_tier == "insurance":
        er_points = _score_equity_ratio_insurance(er)
    elif sector_tier in ("bank_holding", "securities"):
        er_points = _score_equity_ratio_bank(er)
    else:
        er_points = _score_equity_ratio_general(er)

    ratios = {
        "equity_ratio": {"value": round(er, 2) if er is not None else None,
                         "points": er_points, "trend_pct": None},
    }

    # 자본잠식 여부 (bug_015): total_equity ≤ 0 → 거래소 관리종목 1차 트리거 = 강한 부실 신호.
    equity_deficit = te is not None and te <= 0

    if not is_financial:
        # 부채비율: metrics 우선, 없으면 total_liabilities/total_equity×100
        dr = _num(metrics.get("debt_ratio")) if metrics else None
        if dr is None:
            tl = _latest_with_fallback(balance_sheet, "total_liabilities")
            r = _ratio(tl, te)
            dr = r * 100 if r is not None else None
        if equity_deficit:
            # 자본잠식 sentinel: metrics.debt_ratio 음수/비정상값(yfinance 부채/음수자본)이
            # `-1100 < 100 → 4점` false-positive를 내므로, 1점 강제(우선) — bug_015.
            dr_points = 1
            dr_value = round(dr, 2) if dr is not None else None
        else:
            dr_points = _score_debt_ratio(dr)
            dr_value = round(dr, 2) if dr is not None else None
        ratios["debt_ratio"] = {
            "value": dr_value, "points": dr_points, "trend_pct": None,
        }

        # 차입금의존도 = (short_term_debt + long_term_debt) / total_assets × 100
        std = _latest_with_fallback(balance_sheet, "short_term_debt")
        ltd = _latest_with_fallback(balance_sheet, "long_term_debt")
        if ta is None:
            dep = None
        elif std is None and ltd is None:
            dep = 0.0  # 무차입 추정
        else:
            total_debt = (std or 0) + (ltd or 0)
            r = _ratio(total_debt, ta)
            dep = r * 100 if r is not None else None
        ratios["debt_dependency"] = {
            "value": round(dep, 2) if dep is not None else None,
            "points": _score_debt_dependency(dep), "trend_pct": None,
        }

        # 유동비율: metrics 우선(%/배 양형), 없으면 current_assets/current_liabilities
        cr_raw = _num(metrics.get("current_ratio")) if metrics else None
        if cr_raw is None:
            ca = _latest_with_fallback(balance_sheet, "current_assets")
            cl = _latest_with_fallback(balance_sheet, "current_liabilities")
            r = _ratio(ca, cl)
            cr_raw = r if r is not None else None
        cr_pct = _normalize_current_ratio(cr_raw)
        ratios["current_ratio"] = {
            "value": round(cr_pct, 2) if cr_pct is not None else None,
            "points": _score_current_ratio(cr_pct), "trend_pct": None,
        }

    axis = _finalize_axis("stability", ratios, ratio_order)
    if equity_deficit:
        # bug_015: 자본잠식은 점수와 무관하게 진단에 강한 부실 신호로 명시(서술형, §D-7 준수).
        axis["equity_deficit"] = True
        base_diag = axis.get("diagnosis") or ""
        axis["diagnosis"] = f"자본잠식 — 강한 부실 신호. {base_diag}".rstrip()
    return axis


def _finalize_axis(axis_key: str, ratios: dict, ratio_order: list[str]) -> dict:
    """축 점수/등급/진단 조립. 유효 비율 0개면 N/A."""
    # ratio_order 순서로 정렬된 dict 구성 (존재하는 키만)
    ordered = {k: ratios[k] for k in ratio_order if k in ratios}
    score = _axis_score(ordered)
    applicable = score is not None
    grade = _score_to_grade(score)
    if not applicable:
        return {
            "score": None, "grade": "N/A", "applicable": False,
            "na_reason": "유효 비율 데이터 부족",
            "diagnosis": f"{_AXIS_LABEL_KR[axis_key]} 해당 업종 적용 불가(N/A)",
            "ratios": ordered,
        }
    diagnosis = _build_diagnosis(axis_key, score, ordered, ratio_order)
    return {
        "score": score, "grade": grade, "applicable": True, "na_reason": None,
        "diagnosis": diagnosis, "ratios": ordered,
    }


def _na_axis(axis_key: str, ratio_order: list[str], reason: str) -> dict:
    """업종 분기로 적용 불가한 축 (§D-5)."""
    return {
        "score": None, "grade": "N/A", "applicable": False, "na_reason": reason,
        "diagnosis": f"{_AXIS_LABEL_KR[axis_key]} 해당 업종 적용 불가(N/A)",
        "ratios": {k: {"value": None, "points": None, "trend_pct": None}
                   for k in ratio_order},
    }


# ════════════════════ 진입점 (REQ-MARGIN-01) ════════════════════

def compute_ratio_analysis(
    income_stmt: Optional[list],
    balance_sheet: Optional[list],
    cashflow: Optional[list],
    metrics: Optional[dict],
    sector_tier: str = "general",
) -> dict:
    """4축 재무비율 평가 진입점. 4축 점수 + 16비율 + 등급 + 진단 반환.

    Args:
        income_stmt: [{revenue, operating_income, net_income, cogs, interest_expense}] 오래된순
        balance_sheet: [{total_assets, current_assets, receivables, inventories,
                         payables, total_liabilities, current_liabilities,
                         short_term_debt, long_term_debt, total_equity}] 오래된순
        cashflow: [{operating_cf}] 오래된순 (현 16비율에서는 미사용, 향후 확장 hook)
        metrics: {per, pbr, roe, oi_margin, debt_ratio, current_ratio}
        sector_tier: insurance / bank_holding / securities / general

    Returns:
        REQ-MARGIN-01 확정 shape (overall_score/overall_grade/axes/sector_tier/meta).
    """
    income_stmt = income_stmt or []
    balance_sheet = balance_sheet or []
    metrics = metrics or {}
    sector_tier = sector_tier or "general"
    is_financial = sector_tier in _FINANCIAL_TIERS

    axes = {
        "activity": _compute_activity(income_stmt, balance_sheet, is_financial),
        "growth": _compute_growth(income_stmt, balance_sheet, is_financial),
        "profitability": _compute_profitability(income_stmt, balance_sheet, metrics, sector_tier),
        "stability": _compute_stability(balance_sheet, metrics, sector_tier),
    }

    valid_scores = [a["score"] for a in axes.values()
                    if a["applicable"] and a["score"] is not None]
    overall = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None

    return {
        "overall_score": overall,
        "overall_grade": _score_to_grade(overall),
        "axes": axes,
        "sector_tier": sector_tier,
        "meta": {"valid_axis_count": len(valid_scores), "method": _METHOD},
    }


__all__ = ["compute_ratio_analysis"]

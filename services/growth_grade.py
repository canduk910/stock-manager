"""성장주 보조 등급 모듈.

`safety_grade.py`(가치 평가, 7점)와 분리된 별도 등급 트랙.
가치 평가에 구조적으로 불리한 기술/성장 종목이 자동 SKIP되지 않도록
**별도 5지표 20점 만점 성장 등급**(G-A/B/C)을 부여한다.

도메인 자문 합의안 (ValueScreener):
- 매출 CAGR (3년) ........... 4점
- 영업이익 CAGR (3년) ........ 4점
- FCF 추세 (개선/유지/악화) .. 4점
- R&D / 매출 비중 ............. 4점
- 사이클 주도 섹터 정합성 ... 4점

조합 규칙 (OrderAdvisor):
- 가치 A/B+/B 등급은 safety_grade.GRADE_FACTOR 그대로 사용
- 가치 C 등급은 safety_grade.GRADE_FACTOR["C"]=0.25 적용 (별도 모듈에서 조정)
- 가치 D + 성장 G-A → factor=0.3 (소형 분할매수 허용)
- 가치 D + 성장 G-B/G-C → factor=0 (진입 금지)

플랜 출처: .claude/plans/ai-sparkling-starfish.md
"""

from __future__ import annotations

from typing import Optional


# ── 임계값 (ValueScreener 자문) ──────────────────────────────────────────

# 사이클 주도 섹터 정합성 — services/macro_cycle.py LEADER_SECTORS와 호환
# 추가로 한국 섹터 키워드 매핑(섹터 이름이 한국어/영어로 들어올 수 있음)
_LEADER_SECTOR_MAP: dict[str, set[str]] = {
    "recovery": {"XLF", "XLI", "XLB", "Financials", "Industrials", "Materials",
                 "금융", "산업재", "소재", "은행", "건설", "기계"},
    "expansion": {"XLK", "XLY", "XLC", "Technology", "Consumer Discretionary",
                  "Communication Services", "기술", "IT", "반도체", "소프트웨어",
                  "임의소비재", "커뮤니케이션", "인터넷"},
    "overheating": {"XLE", "XLB", "XLP", "Energy", "Materials", "Consumer Staples",
                    "에너지", "필수소비재", "정유", "화학"},
    "contraction": {"XLU", "XLV", "XLP", "Utilities", "Healthcare", "Consumer Staples",
                    "유틸리티", "헬스케어", "필수소비재", "통신"},
}


def _score_revenue_cagr(cagr: Optional[float]) -> int:
    """매출 CAGR(%) 점수. >20=4 / 10-20=3 / 5-10=2 / <5=1."""
    if cagr is None:
        return 1
    if cagr > 20:
        return 4
    if cagr > 10:
        return 3
    if cagr > 5:
        return 2
    return 1


def _score_operating_cagr(cagr: Optional[float]) -> int:
    """영업이익 CAGR(%) 점수. >25=4 / 10-25=3 / 0-10=2 / <0=1.

    영업이익은 매출보다 변동성이 크므로 임계 상향.
    """
    if cagr is None:
        return 1
    if cagr > 25:
        return 4
    if cagr > 10:
        return 3
    if cagr > 0:
        return 2
    return 1


def _score_fcf_trend(cashflow: list[dict]) -> tuple[int, str]:
    """FCF 추세 점수 + 추세 라벨.

    최근 3년 FCF를 비교해 개선/유지/악화 판별.
    개선(증가율>20%) 4점 / 유지(±20%) 3점 / 부분음수 2점 / 3년 음수 1점.
    """
    if not cashflow:
        return 1, "데이터없음"
    fcfs: list[float] = []
    for entry in cashflow[-3:]:
        fcf = entry.get("free_cf") or entry.get("fcf")
        if fcf is None:
            op = entry.get("operating_cf") or entry.get("operating_cashflow") or 0
            capex = abs(entry.get("capex") or entry.get("capital_expenditure") or 0)
            fcf = (op or 0) - capex
        try:
            fcfs.append(float(fcf or 0))
        except (TypeError, ValueError):
            fcfs.append(0.0)

    if not fcfs:
        return 1, "데이터없음"

    neg_count = sum(1 for v in fcfs if v <= 0)
    if neg_count == len(fcfs):
        return 1, "3년 음수"
    if neg_count >= 1:
        # 일부 음수
        return 2, "혼조"

    # 전부 양수 → 추세 판별
    if len(fcfs) < 2:
        return 3, "단년 양수"
    first, last = fcfs[0], fcfs[-1]
    if first <= 0:
        return 3, "회복 중"
    growth = (last - first) / abs(first) * 100
    if growth > 20:
        return 4, f"개선({growth:+.0f}%)"
    if growth > -20:
        return 3, f"유지({growth:+.0f}%)"
    return 2, f"둔화({growth:+.0f}%)"


def _score_rnd_ratio(rnd_ratio: Optional[float]) -> int:
    """R&D / 매출 비중(%) 점수. >15=4 / 8-15=3 / 3-8=2 / <3=1.

    데이터 없으면 2점(중립).
    """
    if rnd_ratio is None:
        return 2
    if rnd_ratio > 15:
        return 4
    if rnd_ratio > 8:
        return 3
    if rnd_ratio > 3:
        return 2
    return 1


def _score_cycle_alignment(sector: Optional[str], cycle_phase: Optional[str]) -> tuple[int, str]:
    """현재 경기 사이클의 주도 섹터와 종목 섹터의 정합성.

    완전 일치=4 / 부분 매칭(같은 카테고리)=3 / 중립=2 / 부적합(반대 사이클)=1.
    """
    if not sector or not cycle_phase:
        return 2, "데이터없음"

    leaders = _LEADER_SECTOR_MAP.get(cycle_phase, set())
    sector_norm = sector.strip()

    # 주도 섹터 직접 매칭
    if sector_norm in leaders:
        return 4, f"주도섹터({cycle_phase})"

    # 반대 사이클 패널티 우선 검사 (확장기 ↔ 수축기 / 회복기 ↔ 과열기)
    # 중요: 반대 사이클 매칭이 부분 매칭보다 우선 — Utilities는 contraction 주도이므로
    # expansion 사이클에서 반대 사이클로 분류되어야 한다.
    opposite = {
        "expansion": "contraction",
        "contraction": "expansion",
        "recovery": "overheating",
        "overheating": "recovery",
    }
    opp_phase = opposite.get(cycle_phase)
    sector_lower = sector_norm.lower()
    sector_words = {w for w in sector_lower.replace("/", " ").replace("-", " ").split() if w}

    def _word_match(leader: str, target_words: set[str], target_lower: str) -> bool:
        """단어 단위 매칭 (부분 문자열 매칭 회피)."""
        leader_lower = leader.lower()
        # 짧은 ETF 심볼/약어(<=3글자, 영문)는 정확 일치만 인정
        if len(leader_lower) <= 3 and leader_lower.isalpha():
            return leader_lower in target_words
        # 긴 키워드는 단어 포함 또는 단어 보유로 매칭
        return leader_lower in target_words or any(
            leader_lower in w or w in leader_lower for w in target_words if len(w) >= 3
        )

    if opp_phase:
        opp_leaders = _LEADER_SECTOR_MAP.get(opp_phase, set())
        for leader in opp_leaders:
            if _word_match(leader, sector_words, sector_lower):
                return 1, f"반대사이클({opp_phase})"

    # 부분 매칭 (단어 단위)
    for leader in leaders:
        if _word_match(leader, sector_words, sector_lower):
            return 3, f"부분일치({leader})"

    return 2, "중립"


# ── 메인 API ─────────────────────────────────────────────────────────────

def compute_growth_grade(
    metrics: Optional[dict],
    income_stmt: Optional[list[dict]] = None,
    cashflow: Optional[list[dict]] = None,
    rnd_ratio: Optional[float] = None,
    sector: Optional[str] = None,
    cycle_phase: Optional[str] = None,
) -> dict:
    """성장 보조 등급 계산.

    Args:
        metrics: {revenue_cagr, operating_cagr, ...} (사전 계산 우선)
        income_stmt: [{year, revenue, operating_income, ...}] — fallback 계산용
        cashflow: [{year, free_cf or operating_cf+capex, ...}]
        rnd_ratio: R&D 매출 비중(%). yfinance/DART 직접 산출 어려움 → None 허용
        sector: 종목 섹터 문자열
        cycle_phase: macro_cycle.determine_cycle_phase()의 phase

    Returns:
        {
            "grade": "G-A" | "G-B" | "G-C",
            "score": int 0~20,
            "details": {
                "revenue_cagr": {"value", "points"},
                "operating_cagr": {"value", "points"},
                "fcf_trend": {"label", "points"},
                "rnd_ratio": {"value", "points"},
                "cycle_alignment": {"label", "points"},
            },
            "thesis": str (자동 생성 thesis 문장),
            "cycle_alignment": str,
        }
    """
    metrics = metrics or {}
    income_stmt = income_stmt or []
    cashflow = cashflow or []

    # 1. 매출 CAGR — 사전 계산 우선, 없으면 직접
    rev_cagr = metrics.get("revenue_cagr")
    if rev_cagr is None:
        rev_cagr = _calc_cagr_from_income(income_stmt, "revenue")
    pts_rev = _score_revenue_cagr(rev_cagr)

    # 2. 영업이익 CAGR
    op_cagr = metrics.get("operating_cagr") or metrics.get("op_income_cagr")
    if op_cagr is None:
        op_cagr = _calc_cagr_from_income(income_stmt, "operating_income")
    pts_op = _score_operating_cagr(op_cagr)

    # 3. FCF 추세
    pts_fcf, fcf_label = _score_fcf_trend(cashflow)

    # 4. R&D 비중
    if rnd_ratio is None:
        rnd_ratio = metrics.get("rnd_ratio") or metrics.get("rd_ratio")
    pts_rnd = _score_rnd_ratio(rnd_ratio)

    # 5. 사이클 정합성
    pts_cyc, cyc_label = _score_cycle_alignment(sector, cycle_phase)

    score = pts_rev + pts_op + pts_fcf + pts_rnd + pts_cyc

    # 등급 컷오프 (ValueScreener 자문)
    if score >= 16:
        grade = "G-A"
    elif score >= 12:
        grade = "G-B"
    else:
        grade = "G-C"

    # thesis 문장 자동 생성
    thesis_parts = []
    if rev_cagr is not None and rev_cagr > 10:
        thesis_parts.append(f"매출 CAGR {rev_cagr:.1f}%")
    if op_cagr is not None and op_cagr > 10:
        thesis_parts.append(f"영업이익 CAGR {op_cagr:.1f}%")
    if fcf_label not in ("데이터없음", "3년 음수"):
        thesis_parts.append(f"FCF {fcf_label}")
    if rnd_ratio is not None and rnd_ratio > 8:
        thesis_parts.append(f"R&D {rnd_ratio:.1f}%")
    if pts_cyc >= 3:
        thesis_parts.append(cyc_label)

    thesis = " · ".join(thesis_parts) if thesis_parts else "성장 모멘텀 약함"

    return {
        "grade": grade,
        "score": score,
        "details": {
            "revenue_cagr": {"value": rev_cagr, "points": pts_rev},
            "operating_cagr": {"value": op_cagr, "points": pts_op},
            "fcf_trend": {"label": fcf_label, "points": pts_fcf},
            "rnd_ratio": {"value": rnd_ratio, "points": pts_rnd},
            "cycle_alignment": {"label": cyc_label, "points": pts_cyc},
        },
        "thesis": thesis,
        "cycle_alignment": cyc_label,
    }


def _calc_cagr_from_income(income_stmt: list[dict], key: str) -> Optional[float]:
    """손익계산서에서 특정 컬럼의 CAGR(%) 계산.

    최소 2년 데이터, 첫 값이 양수여야 함. 음수→양수/양수→음수는 None 반환.
    """
    if not income_stmt or len(income_stmt) < 2:
        return None
    first = income_stmt[0].get(key)
    last = income_stmt[-1].get(key)
    years = len(income_stmt) - 1
    if first is None or last is None or first <= 0 or years <= 0:
        return None
    if last <= 0:
        # 양수 → 음수: 성장률 계산 불가, -100% 부여
        return -100.0
    try:
        return round(((last / first) ** (1 / years) - 1) * 100, 1)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


# ── 가치+성장 결합 등급 (OrderAdvisor 자문) ─────────────────────────────

def combine_grades(value_grade: str, growth_grade: str) -> tuple[float, str]:
    """가치 등급 + 성장 등급 → 최종 factor + 라벨.

    합의 규칙:
    - 가치 A/B+/B → safety_grade.GRADE_FACTOR 그대로 사용 (성장 무관)
    - 가치 C → 0.25 (safety_grade에서 직접 부여)
    - 가치 D + 성장 G-A → 0.30 (성장 트랙 진입, 분할매수 1차 25%만)
    - 가치 D + 성장 G-B/G-C → 0.0 (진입 금지)

    Args:
        value_grade: "A" | "B+" | "B" | "C" | "D"
        growth_grade: "G-A" | "G-B" | "G-C"

    Returns:
        (factor, label) — label은 "가치우위" / "가치+성장혼합" / "성장우위" / "진입금지"
    """
    from services.safety_grade import GRADE_FACTOR

    if value_grade in ("A", "B+", "B"):
        factor = GRADE_FACTOR.get(value_grade, 0.0)
        label = "가치우위"
        if growth_grade == "G-A":
            label = "가치+성장혼합"
        return factor, label

    if value_grade == "C":
        # safety_grade의 C=0.25 사용 — 성장 보조 등급은 라벨만 영향
        factor = GRADE_FACTOR.get("C", 0.25)
        label = "가치C+성장보조" if growth_grade in ("G-A", "G-B") else "가치C"
        return factor, label

    # value_grade == "D"
    if growth_grade == "G-A":
        return 0.30, "성장우위(가치D)"
    return 0.0, "진입금지"


__all__ = [
    "compute_growth_grade",
    "combine_grades",
]

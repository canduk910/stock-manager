"""AI 포트폴리오 자문 서비스.

잔고 데이터를 분석하여 포트폴리오 진단, 리밸런싱 제안, 매매 실행안을 생성한다.
OpenAI GPT를 사용하며, 결과는 stock/cache.py에 30분 TTL로 캐싱.
"""

from __future__ import annotations

import hashlib
import json
import logging

from config import ADVISOR_CACHE_TTL_HOURS, OPENAI_API_KEY, OPENAI_MODEL
from services.exceptions import ConfigError, ExternalAPIError, NotFoundError, PaymentRequiredError
from services.macro_regime import determine_regime as _shared_determine_regime
from stock import advisory_store
from stock.cache import get_cached, set_cached
from stock.db_base import now_kst, now_kst_iso

logger = logging.getLogger(__name__)


# ── 캐시 키 ──────────────────────────────────────────────────────────────────

def _compute_cache_key(balance_data: dict) -> str:
    """보유종목 구성(code+quantity)으로 SHA256 캐시 키 생성."""
    pairs: list[tuple[str, str]] = []
    for s in balance_data.get("stock_list") or []:
        pairs.append((s.get("code", ""), str(s.get("quantity", ""))))
    for s in balance_data.get("overseas_list") or []:
        pairs.append((s.get("code", ""), str(s.get("quantity", ""))))
    pairs.sort()
    h = hashlib.sha256(json.dumps(pairs, ensure_ascii=False).encode()).hexdigest()
    return f"advisor:portfolio:{h}"


# ── 컨텍스트 구성 ────────────────────────────────────────────────────────────

def _safe_float(val, default=0.0) -> float:
    """문자열/숫자를 안전하게 float 변환."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _fetch_52w_high(code: str, market: str) -> int | float | None:
    """종목의 52주 고가를 가져온다. 6시간 TTL 캐싱."""
    cache_key = f"advisor:52w:{market}:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        # 캐시 값은 {"value": num} 형태로 감싸서 저장 (None도 캐싱 가능하도록)
        if isinstance(cached, dict):
            return cached.get("value")
        return cached
    try:
        if market == "KR":
            from stock.market import fetch_market_metrics
            m = fetch_market_metrics(code)
            value = m.get("high_52")
        else:
            from stock.yf_client import _ticker, _safe
            t = _ticker(code)
            value = _safe(t.fast_info.year_high)
    except Exception:
        value = None
    try:
        set_cached(cache_key, {"value": value}, ttl_hours=6)
    except Exception:
        pass
    return value


def _extract_report_summary(report_data: dict) -> dict:
    """개별 리포트 JSON에서 포트폴리오 프롬프트용 핵심 필드 추출.

    v1 리포트 구조: {종합투자의견: {등급, 요약, 근거}, 전략별평가: {안전마진: {할인율}}, 리스크요인: [{요인}]}
    v2(Phase 3): schema_version='v2' + 종목등급/등급점수 필드 추가 예정. v1 리포트는 grade=None.
    """
    if not isinstance(report_data, dict):
        return {"grade": None, "summary_2lines": None, "discount_rate": None, "risks": []}

    # 실제 저장 구조: advisory_store.get_latest_report() → {report_id, model, report: {...원본JSON...}, created_at}
    report_body = report_data.get("report") or report_data
    if not isinstance(report_body, dict):
        return {"grade": None, "summary_2lines": None, "discount_rate": None, "risks": []}

    opinion = report_body.get("종합투자의견") or {}
    # v1: 등급 = "매수/중립/매도", v2에서는 "종목등급"(A/B+/B/C/D) 필드 별도
    grade = report_body.get("종목등급") or None  # v1은 None

    # 요약 180자 제한
    summary = opinion.get("요약") if isinstance(opinion, dict) else None
    if isinstance(summary, str) and len(summary) > 180:
        summary = summary[:177] + "..."

    # 안전마진 할인율
    discount = None
    strat = report_body.get("전략별평가") or {}
    margin = strat.get("안전마진") if isinstance(strat, dict) else None
    if isinstance(margin, dict):
        discount = margin.get("할인율")

    # 리스크 상위 2개, 각 50자 제한
    risks_raw = report_body.get("리스크요인") or []
    risks: list[str] = []
    if isinstance(risks_raw, list):
        for r in risks_raw[:2]:
            if isinstance(r, dict):
                txt = r.get("요인") or r.get("name") or ""
            else:
                txt = str(r)
            if txt:
                if len(txt) > 50:
                    txt = txt[:47] + "..."
                risks.append(txt)

    return {
        "grade": grade,
        "summary_2lines": summary,
        "discount_rate": discount,
        "risks": risks,
    }


def _fetch_latest_report_summary(code: str, market: str) -> dict:
    """종목의 최신 AI 리포트 요약 반환. 리포트 없으면 빈 dict."""
    try:
        latest = advisory_store.get_latest_report(code, market)
    except Exception as e:
        logger.debug("개별 리포트 조회 실패 [%s %s]: %s", code, market, e)
        return {"grade": None, "summary_2lines": None, "discount_rate": None, "risks": []}
    if not latest:
        return {"grade": None, "summary_2lines": None, "discount_rate": None, "risks": []}
    return _extract_report_summary(latest)


def _build_context(balance_data: dict) -> dict:
    """잔고 API 응답 → GPT 프롬프트용 컨텍스트 구조체 변환."""
    total_eval = _safe_float(balance_data.get("total_evaluation"))
    deposit = _safe_float(balance_data.get("deposit"))
    deposit_domestic = _safe_float(balance_data.get("deposit_domestic"))
    deposit_overseas_krw = _safe_float(balance_data.get("deposit_overseas_krw"))
    stock_eval_domestic = _safe_float(balance_data.get("stock_eval_domestic"))
    stock_eval_overseas = _safe_float(balance_data.get("stock_eval_overseas_krw"))

    holdings: list[dict] = []

    # 국내주식
    for s in balance_data.get("stock_list") or []:
        eval_amt = _safe_float(s.get("eval_amount"))
        weight = (eval_amt / total_eval * 100) if total_eval > 0 else 0
        code = s.get("code", "")
        cur = _safe_float(s.get("current_price"))
        h52 = _fetch_52w_high(code, "KR")
        drop = round((cur - h52) / h52 * 100, 1) if cur and h52 and h52 > 0 else None
        report_summary = _fetch_latest_report_summary(code, "KR")
        holdings.append({
            "name": s.get("name", ""),
            "code": code,
            "market": "KR",
            "exchange": s.get("exchange"),
            "quantity": s.get("quantity", "0"),
            "avg_price": s.get("avg_price"),
            "current_price": s.get("current_price"),
            "profit_rate": s.get("profit_rate"),
            "eval_amount": s.get("eval_amount"),
            "weight_pct": round(weight, 2),
            "per": s.get("per"),
            "pbr": s.get("pbr"),
            "roe": s.get("roe"),
            "dividend_yield": s.get("dividend_yield"),
            "high_52": h52,
            "drop_from_high": drop,
            "latest_report_grade": report_summary.get("grade"),
            "latest_report_summary": report_summary.get("summary_2lines"),
            "latest_report_discount_rate": report_summary.get("discount_rate"),
            "latest_report_risks": report_summary.get("risks") or [],
        })

    # 해외주식
    for s in balance_data.get("overseas_list") or []:
        eval_krw = _safe_float(s.get("eval_amount_krw"))
        weight = (eval_krw / total_eval * 100) if total_eval > 0 else 0
        code_us = s.get("code", "")
        cur_us = _safe_float(s.get("current_price"))
        h52_us = _fetch_52w_high(code_us, "US")
        drop_us = round((cur_us - h52_us) / h52_us * 100, 1) if cur_us and h52_us and h52_us > 0 else None
        report_summary_us = _fetch_latest_report_summary(code_us, "US")
        holdings.append({
            "name": s.get("name", ""),
            "code": code_us,
            "market": "US",
            "exchange": s.get("exchange"),
            "currency": s.get("currency", "USD"),
            "quantity": s.get("quantity", "0"),
            "avg_price": s.get("avg_price"),
            "current_price": s.get("current_price"),
            "profit_rate": s.get("profit_rate"),
            "eval_amount_foreign": s.get("eval_amount"),
            "eval_amount_krw": s.get("eval_amount_krw"),
            "weight_pct": round(weight, 2),
            "per": s.get("per"),
            "pbr": s.get("pbr"),
            "roe": s.get("roe"),
            "dividend_yield": s.get("dividend_yield"),
            "high_52": h52_us,
            "drop_from_high": drop_us,
            "latest_report_grade": report_summary_us.get("grade"),
            "latest_report_summary": report_summary_us.get("summary_2lines"),
            "latest_report_discount_rate": report_summary_us.get("discount_rate"),
            "latest_report_risks": report_summary_us.get("risks") or [],
        })

    # 집중도 계산
    weights = sorted([h["weight_pct"] for h in holdings], reverse=True)
    top3_weight = sum(weights[:3]) if len(weights) >= 3 else sum(weights)
    hhi = sum(w ** 2 for w in weights)

    domestic_ratio = (stock_eval_domestic / total_eval * 100) if total_eval > 0 else 0
    overseas_ratio = (stock_eval_overseas / total_eval * 100) if total_eval > 0 else 0

    # Phase 2-8: 가중 평균 등급 + 등급 분포 + 체제 정합성
    # latest_report_grade는 v1에서는 None (Phase 3 DB 스키마 확장 후 v2 리포트가 생기면 값 채워짐)
    GRADE_SCORE_MAP = {"A": 26, "B+": 21.5, "B": 17.5, "C": 13.5, "D": 8.0}  # 등급 구간 중심값
    grade_distribution = {"A": 0, "B+": 0, "B": 0, "C": 0, "D": 0, "unknown": 0}
    weighted_score_sum = 0.0
    graded_weight_sum = 0.0
    for h in holdings:
        g = h.get("latest_report_grade")
        if g in GRADE_SCORE_MAP:
            grade_distribution[g] += 1
            weighted_score_sum += h.get("weight_pct", 0) * GRADE_SCORE_MAP[g]
            graded_weight_sum += h.get("weight_pct", 0)
        else:
            grade_distribution["unknown"] += 1
    portfolio_grade_weighted_avg = (
        round(weighted_score_sum / graded_weight_sum, 1) if graded_weight_sum > 0 else None
    )

    # 체제 정합성 점수 — 가중 평균 등급 + 주식 비중 정합
    stock_pct = domestic_ratio + overseas_ratio
    regime_alignment_score = None  # _build_prompt에서 체제 결정 후 계산

    return {
        "total_evaluation_krw": total_eval,
        "deposit_total_krw": deposit,
        "deposit_domestic_krw": deposit_domestic,
        "deposit_overseas_krw": deposit_overseas_krw,
        "domestic_ratio_pct": round(domestic_ratio, 1),
        "overseas_ratio_pct": round(overseas_ratio, 1),
        "stock_total_pct": round(stock_pct, 1),
        "num_holdings": len(holdings),
        "top3_concentration_pct": round(top3_weight, 1),
        "hhi": round(hhi, 1),
        "holdings": holdings,
        "has_fno": bool(balance_data.get("futures_list")),
        # Phase 2-8 신규 필드
        "portfolio_grade_weighted_avg": portfolio_grade_weighted_avg,
        "grade_distribution": grade_distribution,
        "regime_alignment_score": regime_alignment_score,  # analyze_portfolio에서 주입
        "analysis_date": now_kst_iso(),
    }


# ── 프롬프트 ─────────────────────────────────────────────────────────────────

_REGIME_CASH_RULES = {
    "accumulation": ("25%", "75%", "적극 투자 가능. 현금 25% 이상 유지."),
    "selective":    ("35%", "65%", "선별 투자만 허용. 현금 부족 시 일부 매도 권고."),
    "cautious":     ("50%", "50%", "주식 비중 축소 방향으로 리밸런싱."),
    "defensive":    ("75%", "25%", "대부분 종목 매도 권고. 신규 매수 금지."),
}


def _determine_regime(sentiment: dict) -> tuple[str, str]:
    """sentiment → (regime, regime_desc) 반환 — 공용 모듈 위임."""
    result = _shared_determine_regime(sentiment)
    return result["regime"], result["regime_desc"]


def _get_macro_context() -> dict:
    """매크로 심리 데이터 수집 (캐시 활용, 실패 시 빈 dict)."""
    try:
        from services import macro_service
        return macro_service.get_sentiment()
    except Exception as e:
        logger.debug("매크로 컨텍스트 수집 실패: %s", e)
        return {}


_CONTRARIAN_RULES = """
역발상 매수 (Contrarian Buy) — cautious/selective 체제 한정:
19. 역발상 매수 후보 조건 — 아래 5개를 모두 충족해야 한다:
    a. 52주 고점 대비 -30% 이상 하락
    b. PBR < 1.0 (자산 가치 대비 저평가)
    c. 부채비율 < 100%
    d. 최근 4분기 영업이익 흑자 유지
    e. FCF(잉여현금흐름) 양수
20. 다음 중 하나라도 해당하면 역발상 매수 제외 ("가치 함정" 경고):
    a. 분기 영업이익 적자 전환
    b. 부채비율 전년 대비 30%p 이상 급증
    c. 업종 구조적 쇠퇴
    d. 2년 이상 연속 적자
21. trades.reason에 "[역발상]" 접두어 필수 표기.
22. 역발상 매수 긴급도: -30~40% → this_month, -40~50% → this_week. immediate 금지.
23. 역발상 매수 손절: 진입가 대비 -20% (일반 -10~15%보다 넓음). 분기 영업적자 전환 시 즉시 손절.
24. 역발상 매수 포지션 한도:
    - selective: 종목당 3%, 역발상 총합 10%
    - cautious: 종목당 1.5%, 역발상 총합 7.5%
25. 분할 매수: 1차 30%(진입) → 2차 30%(-10% 추가 하락 시) → 3차 40%(-20% 추가 하락 시). 1차에서 전량 매수 금지.

보유종목 vs 신규종목 판단 분리:
26. 이미 보유 중인 -15% 초과 종목: 기존 규칙 13-15 적용 (물타기/손절).
27. 미보유 종목 -30% 이상: 역발상 매수 조건(규칙 19) 판별.
28. 보유 중 + 역발상 추가 매수: 물타기 조건(14) + 역발상 조건(19) 양쪽 모두 충족 시만 허용. trades.reason에 "[역발상 물타기]" 명시.

"""


def _build_system_prompt(regime: str, cash_pct: float) -> str:
    """체제별 투자 원칙이 포함된 포트폴리오 자문 시스템 프롬프트."""
    cash_min, stock_max, cash_guidance = _REGIME_CASH_RULES.get(regime, _REGIME_CASH_RULES["selective"])
    contrarian_section = _CONTRARIAN_RULES if regime in ("cautious", "selective") else ""
    cash_warning = ""
    if regime == "defensive":
        cash_warning = f"\n【중요】 현재 현금 비중 {cash_pct}%는 defensive 체제 권고({cash_min}) 대비 {'부족' if cash_pct < 75 else '적정'}합니다. 신규 매수를 추천하지 마세요."
    elif cash_pct < float(cash_min.replace('%', '')):
        cash_warning = f"\n현재 현금 비중 {cash_pct}%는 {regime} 체제 권고({cash_min}) 대비 부족합니다. 현금 확보를 위한 매도를 우선 검토하세요."

    return f"""당신은 한국 주식시장 전문 포트폴리오 투자자문 AI입니다.
사용자의 실제 보유 포트폴리오 데이터를 분석하여 반드시 아래 JSON 형식으로만 응답하세요.

{{
  "diagnosis": {{
    "summary": "전체 포트폴리오 진단 요약 (2~3문장)",
    "risk_level": "high 또는 medium 또는 low",
    "total_score": 0~100 정수 (포트폴리오 건전성 점수),
    "concentration_risk": "상위 3종목 비중 합계 기반 집중도 평가",
    "sector_analysis": [
      {{"sector": "섹터명", "weight_pct": 비중, "assessment": "편중/적정/부족 평가"}}
    ],
    "currency_exposure": "원화/외화 비중 평가"
  }},
  "rebalancing": [
    {{
      "stock_name": "종목명",
      "stock_code": "종목코드",
      "action": "increase 또는 reduce 또는 hold 또는 exit",
      "current_weight": 현재비중,
      "suggested_weight": 제안비중,
      "priority": 1~5 (1이 가장 높음),
      "reason": "구체적 근거"
    }}
  ],
  "trades": [
    {{
      "stock_name": "종목명",
      "stock_code": "종목코드",
      "market": "KR 또는 US",
      "action": "buy 또는 sell",
      "qty": 수량(정수),
      "target_price": 목표가(정수 또는 소수점2자리),
      "stop_loss": 손절가(정수 또는 소수점2자리),
      "position_pct": 매매 후 해당 종목 예상 비중(%),
      "urgency": "immediate 또는 this_week 또는 this_month",
      "urgency_reason": "긴급도 판단 근거",
      "reason": "매매 근거"
    }}
  ],
  "market_context": "현재 시장 상황에 대한 간략한 코멘트",
  "disclaimer": "본 분석은 AI가 생성한 참고용 자료이며, 실제 투자 판단과 그에 따른 책임은 전적으로 사용자에게 있습니다."
}}

분석 원칙:
1. 단일 섹터 비중이 40%를 넘으면 반드시 경고할 것
2. 손실 중인 종목은 손절/물타기/홀딩 중 하나를 명확히 제안할 것
3. PER/PBR/ROE/배당수익률을 밸류에이션 판단에 활용할 것
4. 국내/해외 통화 분산도를 평가에 반영할 것
5. 상위 3종목 합산 비중이 60% 이상이면 집중도 위험으로 판단할 것
6. 리밸런싱과 매매 제안은 종목명과 종목코드를 반드시 포함할 것
7. 한국어로 작성할 것
8. 업종(섹터)은 종목명/코드에서 추론하여 분석할 것

개별 종목 AI 리포트 연계 (holdings[].latest_report_*):
A. 각 종목의 `latest_report_summary` 와 `latest_report_risks` 는 개별 종목 AI 애널리스트의 심층 판단이다. 포트폴리오 관점에서 재평가하되, 상충 시 reasoning에 개별 리포트의 어느 근거에 동의/반대하는지 명시하라.
B. `latest_report_discount_rate < 0` (음수) 종목은 Graham Number 대비 고평가 상태 → 비중 축소(reduce) 또는 매도(exit) 우선 검토.
C. `latest_report_discount_rate > 30` 종목은 안전마진 충분 → 체제 허용 시 비중 확대(increase) 후보.
D. `latest_report_risks`에 명시된 리스크 2개 이상이면 해당 종목 priority=1(최우선) 재검토.
E. 우선순위 원칙 — 기본적으로 포트폴리오 최적화(집중도/체제 현금비중/가중평균 등급/섹터 편중) 4대 제약이 개별 리포트 판단보다 우선. 단, 상충 시 reasoning에 다음 두 가지를 모두 명시:
   1) 동의하는 개별 리포트 근거(종목명+근거)
   2) 반대하는 근거 + 포트폴리오 관점의 반대 이유 (4대 제약 중 어느 것)
F. 개별 신호를 뒤집지 않는 예외 3건 (필수 승계):
   1) `latest_report_risks`에 "Value Trap" 또는 "가치 함정" 단어 포함 + 개별 AI가 "매도" 권고 → 매도(exit) 필수 승계 (포트폴리오 최적화로 상쇄 불가)
   2) 기술 시그널 극단 과매수(RSI>80) + 개별 AI 매도 시그널 → "신규 매수" 권고 금지 (기존 보유 유지는 허용)
   3) `latest_report_risks`에 "분식회계", "횡령", "상장폐지", "감사의견 거절", "감사의견 한정", "자본잠식", "회계이상" 중 하나라도 포함 → 즉시 청산(immediate + exit). 포트폴리오 집중도·체제·가중등급과 무관.
G. 포트폴리오 가중 평균 등급이 B 미만(weighted_avg score<16) 또는 C/D 등급 종목이 과반이면 신규 편입 전면 보류 + 기존 C/D 등급 종목 우선 정리 권고 (체제와 무관).

포지션 사이징:
9.  단일 종목 투자금액은 총 평가금액의 5% 초과 금지
10. 1회 매수 주문 금액은 예수금의 30% 초과 금지
11. 매수 추천 시 분할 매수 권고 (1차 50% → 2차 30% → 3차 20%)
12. 총 주식 비중은 {stock_max}를 초과하지 않는다. 현금 {cash_min} 이상 유지.

손실 종목 처리:
13. -7%~-15% 주의: 재무 건전성 재점검 후 물타기/홀딩 택1 (PBR<1.0+부채비율<100%만 물타기)
14. -15% 초과 위험: 손절 우선 검토 (PBR<0.7+부채비율<100%+FCF양수만 물타기 허용)
15. 고평가(PER>업종평균1.5배 또는 PBR>2.0) 손실 종목은 비중 축소/손절 우선

긴급도 판단:
16. immediate: 손절 대상(-15%+재무악화), RSI>80 과매수 고비중 종목, 급락(-5%↑)+거래량급증
17. this_week: MACD 데드크로스 고비중(>5%) 비중 축소, 실적 발표 D-3 선제 조정
18. this_month: 리밸런싱 비중 조정, 분할 매수 진행, 현금 비중 복원

{contrarian_section}매크로 체제: {regime} ({cash_guidance}){cash_warning}"""


def _build_prompt(context: dict, macro_ctx: dict, regime: str, regime_desc: str) -> tuple[str, str]:
    """시스템 프롬프트와 유저 프롬프트를 반환."""
    cash_pct = context.get("deposit_total_krw", 0)
    total = context.get("total_evaluation_krw", 1) or 1
    cash_ratio = round(cash_pct / total * 100, 1)

    system_prompt = _build_system_prompt(regime, cash_ratio)

    # 매크로 요약을 컨텍스트에 추가
    macro_summary = {}
    if macro_ctx:
        fg = macro_ctx.get("fear_greed") or {}
        macro_summary = {
            "regime": regime,
            "regime_desc": regime_desc,
            "fear_greed": fg.get("value") or fg.get("score"),
            "vix": (macro_ctx.get("vix") or {}).get("value"),
            "buffett_ratio": (macro_ctx.get("buffett") or {}).get("ratio"),
        }
    context_with_macro = {**context, "macro": macro_summary}

    user_msg = f"내 포트폴리오를 분석해주세요.\n\n{json.dumps(context_with_macro, ensure_ascii=False, indent=2)}"
    return system_prompt, user_msg


# ── JSON 파싱 ────────────────────────────────────────────────────────────────

def _parse_response(content: str) -> dict:
    """OpenAI 응답 JSON 파싱. 실패 시 원문 포함."""
    try:
        return json.loads(content)
    except Exception:
        return {"raw": content}


# ── 오케스트레이션 ───────────────────────────────────────────────────────────

def analyze_portfolio(balance_data: dict, force_refresh: bool = False) -> dict:
    """포트폴리오 AI 자문 전체 파이프라인.

    1. OPENAI_API_KEY 확인
    2. 캐시 확인 (force_refresh=False일 때)
    3. 컨텍스트 구성 → 프롬프트 빌드 → OpenAI 호출
    4. 결과 캐싱 → 반환
    """
    if not OPENAI_API_KEY:
        raise ConfigError("OPENAI_API_KEY가 설정되지 않았습니다.")

    cache_key = _compute_cache_key(balance_data)

    # 캐시 확인
    if not force_refresh:
        cached = get_cached(cache_key)
        if cached:
            logger.info("포트폴리오 자문 캐시 히트: %s", cache_key[:20])
            return {
                "data": cached.get("data", cached),
                "cached": True,
                "analyzed_at": cached.get("analyzed_at", ""),
                "report_id": cached.get("report_id"),
            }

    # 컨텍스트 구성
    context = _build_context(balance_data)

    # 매크로 컨텍스트 수집
    macro_ctx = _get_macro_context()
    regime, regime_desc = _determine_regime(macro_ctx)

    # Phase 2-8: 체제 정합성 점수 주입 (가중 평균 등급 → grade_score 변환)
    try:
        from services.safety_grade import compute_regime_alignment
        weighted_avg = context.get("portfolio_grade_weighted_avg")
        context["regime_alignment_score"] = compute_regime_alignment(
            regime=regime,
            grade_score=int(weighted_avg) if weighted_avg is not None else None,
            fcf_years_positive=None,  # 포트폴리오 차원은 FCF 데이터 없음 (None → 중립 50점)
            stock_pct=context.get("stock_total_pct"),
        )
    except Exception as e:
        logger.debug("체제 정합성 계산 실패: %s", e)
        context["regime_alignment_score"] = None

    system_prompt, user_prompt = _build_prompt(context, macro_ctx, regime, regime_desc)

    # OpenAI 호출 (Phase 3: 재시도 로직)
    def _call_portfolio_openai(max_tokens: int) -> tuple[str, str]:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or "{}", resp.choices[0].finish_reason or "stop"

    try:
        import time as _time

        content, finish_reason = _call_portfolio_openai(10000)

        # 토큰 잘림 1차 재시도 (12000)
        if finish_reason == "length":
            logger.warning("포트폴리오 자문 토큰 잘림 1차 — 12000으로 재시도")
            _time.sleep(1)
            content, finish_reason = _call_portfolio_openai(12000)
            if finish_reason == "length":
                raise ExternalAPIError("포트폴리오 자문 응답이 토큰 제한으로 잘렸습니다.")

        analysis = _parse_response(content)

        # GPT 응답 파싱 실패 시 에러 반환
        if "raw" in analysis and "diagnosis" not in analysis:
            logger.error("GPT 응답 JSON 파싱 실패. 원문 길이: %d", len(content))
            raise ExternalAPIError("AI 응답을 파싱할 수 없습니다. 다시 시도해주세요.")
    except (ConfigError, PaymentRequiredError, ExternalAPIError):
        raise
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise PaymentRequiredError(
                "OpenAI API 크레딧이 부족합니다. platform.openai.com에서 결제 정보를 확인해주세요.",
            )
        # 일반 에러 1회 재시도 (backoff 2초)
        import time as _time
        logger.warning("포트폴리오 OpenAI 1차 실패: %s — 2초 후 재시도", err_str[:200])
        _time.sleep(2)
        try:
            content, _ = _call_portfolio_openai(10000)
            analysis = _parse_response(content)
            if "raw" in analysis and "diagnosis" not in analysis:
                raise ExternalAPIError("AI 응답을 파싱할 수 없습니다.")
        except Exception as e2:
            raise ExternalAPIError(f"OpenAI 호출 실패: {str(e2)}")

    analyzed_at = now_kst_iso()

    # DB 영구 저장 (Phase 3 확장 필드)
    weighted_avg = context.get("portfolio_grade_weighted_avg")
    report_id = advisory_store.save_portfolio_report(
        OPENAI_MODEL, analysis,
        weighted_grade_avg=weighted_avg,
        regime=regime,
        schema_version="v2" if weighted_avg is not None else "v1",
    )

    # 캐시 저장
    cache_value = {"data": analysis, "analyzed_at": analyzed_at, "report_id": report_id}
    set_cached(cache_key, cache_value, ttl_hours=ADVISOR_CACHE_TTL_HOURS)

    return {
        "data": analysis,
        "cached": False,
        "analyzed_at": analyzed_at,
        "report_id": report_id,
    }


# ── 이력 조회 ────────────────────────────────────────────────────────────────

def get_report_history(limit: int = 20) -> list[dict]:
    """포트폴리오 자문 이력 목록."""
    return advisory_store.get_portfolio_report_history(limit)


def get_report_by_id(report_id: int) -> dict:
    """특정 자문 리포트 상세 조회."""
    result = advisory_store.get_portfolio_report_by_id(report_id)
    if not result:
        raise NotFoundError("해당 자문 리포트를 찾을 수 없습니다.")
    return result

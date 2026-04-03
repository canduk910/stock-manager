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
        holdings.append({
            "name": s.get("name", ""),
            "code": s.get("code", ""),
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
        })

    # 해외주식
    for s in balance_data.get("overseas_list") or []:
        eval_krw = _safe_float(s.get("eval_amount_krw"))
        weight = (eval_krw / total_eval * 100) if total_eval > 0 else 0
        holdings.append({
            "name": s.get("name", ""),
            "code": s.get("code", ""),
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
        })

    # 집중도 계산
    weights = sorted([h["weight_pct"] for h in holdings], reverse=True)
    top3_weight = sum(weights[:3]) if len(weights) >= 3 else sum(weights)
    hhi = sum(w ** 2 for w in weights)

    domestic_ratio = (stock_eval_domestic / total_eval * 100) if total_eval > 0 else 0
    overseas_ratio = (stock_eval_overseas / total_eval * 100) if total_eval > 0 else 0

    return {
        "total_evaluation_krw": total_eval,
        "deposit_total_krw": deposit,
        "deposit_domestic_krw": deposit_domestic,
        "deposit_overseas_krw": deposit_overseas_krw,
        "domestic_ratio_pct": round(domestic_ratio, 1),
        "overseas_ratio_pct": round(overseas_ratio, 1),
        "num_holdings": len(holdings),
        "top3_concentration_pct": round(top3_weight, 1),
        "hhi": round(hhi, 1),
        "holdings": holdings,
        "has_fno": bool(balance_data.get("futures_list")),
        "analysis_date": now_kst_iso(),
    }


# ── 프롬프트 ─────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 한국 주식시장 전문 포트폴리오 투자자문 AI입니다.
사용자의 실제 보유 포트폴리오 데이터를 분석하여 반드시 아래 JSON 형식으로만 응답하세요.

{
  "diagnosis": {
    "summary": "전체 포트폴리오 진단 요약 (2~3문장)",
    "risk_level": "high 또는 medium 또는 low",
    "total_score": 0~100 정수 (포트폴리오 건전성 점수),
    "concentration_risk": "상위 3종목 비중 합계 기반 집중도 평가",
    "sector_analysis": [
      {"sector": "섹터명", "weight_pct": 비중, "assessment": "편중/적정/부족 평가"}
    ],
    "currency_exposure": "원화/외화 비중 평가"
  },
  "rebalancing": [
    {
      "stock_name": "종목명",
      "stock_code": "종목코드",
      "action": "increase 또는 reduce 또는 hold 또는 exit",
      "current_weight": 현재비중,
      "suggested_weight": 제안비중,
      "priority": 1~5 (1이 가장 높음),
      "reason": "구체적 근거"
    }
  ],
  "trades": [
    {
      "stock_name": "종목명",
      "stock_code": "종목코드",
      "market": "KR 또는 US",
      "action": "buy 또는 sell",
      "qty": 수량(정수),
      "target_price": 목표가(정수 또는 소수점2자리),
      "urgency": "immediate 또는 this_week 또는 this_month",
      "reason": "매매 근거"
    }
  ],
  "market_context": "현재 시장 상황에 대한 간략한 코멘트",
  "disclaimer": "본 분석은 AI가 생성한 참고용 자료이며, 실제 투자 판단과 그에 따른 책임은 전적으로 사용자에게 있습니다."
}

분석 원칙:
1. 단일 섹터 비중이 40%를 넘으면 반드시 경고할 것
2. 손실 중인 종목은 손절/물타기/홀딩 중 하나를 명확히 제안할 것
3. 매매 수량은 예수금 범위 내에서 현실적으로 산출할 것 (너무 큰 수량 금지)
4. PER/PBR/ROE/배당수익률을 밸류에이션 판단에 활용할 것
5. 국내/해외 통화 분산도를 평가에 반영할 것
6. 상위 3종목 합산 비중이 60% 이상이면 집중도 위험으로 판단할 것
7. 리밸런싱과 매매 제안은 종목명과 종목코드를 반드시 포함할 것
8. 한국어로 작성할 것"""


def _build_prompt(context: dict) -> tuple[str, str]:
    """시스템 프롬프트와 유저 프롬프트를 반환."""
    user_msg = f"내 포트폴리오를 분석해주세요.\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    return _SYSTEM_PROMPT, user_msg


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
    system_prompt, user_prompt = _build_prompt(context)

    # OpenAI 호출
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=3000,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        analysis = _parse_response(content)
    except (ConfigError, PaymentRequiredError, ExternalAPIError):
        raise
    except Exception as e:
        err_str = str(e)
        if "insufficient_quota" in err_str or "429" in err_str:
            raise PaymentRequiredError(
                "OpenAI API 크레딧이 부족합니다. platform.openai.com에서 결제 정보를 확인해주세요.",
            )
        raise ExternalAPIError(f"OpenAI 호출 실패: {err_str}")

    analyzed_at = now_kst_iso()

    # DB 영구 저장
    report_id = advisory_store.save_portfolio_report(OPENAI_MODEL, analysis)

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

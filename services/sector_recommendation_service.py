"""GPT 기반 섹터 추천 서비스.

매크로 현황(체제/VIX/버핏/공포탐욕/지수/뉴스) + 실제 섹터 ETF 수익률을 입력으로
3가지 컨셉(모멘텀/역발상/3개월선점)의 탑픽 섹터를 추천한다.

모멘텀/역발상 분류는 실제 가격 데이터(섹터 ETF 수익률)에 기반한다.
- 모멘텀: 1M/3M 수익률 상위 섹터 (실제 상승 추세)
- 역발상: 1M/3M 수익률 하위 또는 음수 섹터 (낙폭 과대, 반등 잠재력)

캐시: macro_store 일일 캐싱 — GPT 호출은 market당 하루 1회.
OPENAI_API_KEY 미설정 시 빈 결과 반환 (graceful degradation).
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from config import OPENAI_API_KEY, OPENAI_MODEL
from stock.macro_store import get_today as get_macro_today, save_today as save_macro_today
from stock.db_base import now_kst_iso

logger = logging.getLogger(__name__)


def generate_sector_recommendations(
    regime_data: dict,
    indices_data: dict,
    news_data: dict,
    market: str,
    sector_returns: Optional[list[dict]] = None,
) -> dict:
    """GPT 기반 3컨셉 섹터 추천. macro_store 일일 캐싱.

    Args:
        regime_data: determine_regime() 반환값 (regime, vix, buffett_ratio, ...)
        indices_data: macro_service.get_indices() 반환값
        news_data: macro_service.get_news() 반환값
        market: "KR" | "US"
        sector_returns: 섹터 ETF 수익률 리스트 (fetch_sector_returns / fetch_sector_returns_kr)

    Returns:
        {"generated_at": str, "concepts": [...]} 또는 빈 {"concepts": []}
    """
    cache_key = f"sector_rec:{market}"

    # 일일 캐시 히트
    cached = get_macro_today(cache_key)
    if cached:
        logger.info("섹터 추천 캐시 히트: %s", cache_key)
        return cached

    if not OPENAI_API_KEY:
        logger.info("OPENAI_API_KEY 미설정 — 섹터 추천 건너뜀")
        return {"concepts": []}

    system_prompt = _build_system_prompt(market)
    user_prompt = _build_user_prompt(regime_data, indices_data, news_data, market, sector_returns)

    try:
        result = _call_openai(system_prompt, user_prompt)
        result["generated_at"] = now_kst_iso()
        save_macro_today(cache_key, result)
        logger.info("섹터 추천 생성 완료: %s (%d concepts)", market, len(result.get("concepts", [])))
        return result
    except Exception as e:
        logger.error("섹터 추천 GPT 호출 실패: %s", e)
        return {"concepts": []}


def _build_system_prompt(market: str) -> str:
    market_label = "한국(KRX)" if market == "KR" else "미국(NYSE/NASDAQ)"
    code_rule = "6자리 KRX 종목코드" if market == "KR" else "NYSE/NASDAQ 티커 심볼"
    return (
        f"당신은 {market_label} 주식 시장의 섹터 전략 전문가입니다.\n"
        "현재 시장 체제(regime), 매크로 지표, 뉴스 헤드라인을 분석하여 "
        "3가지 컨셉의 유망 섹터를 추천합니다.\n\n"
        "【컨셉 정의】\n"
        "1. momentum (모멘텀): 현재 강한 상승 추세를 보이는 업종. 추세 지속 가능성이 높은 섹터.\n"
        "2. contrarian (역발상): 과매도되었거나 저평가 상태의 업종. 반등 잠재력이 큰 섹터.\n"
        "3. forward_3m (3개월 선점): 향후 3개월 내 모멘텀이 예상되는 업종. "
        "정책/실적/이벤트 기반 선제적 포지셔닝.\n\n"
        "【규칙】\n"
        "- 각 컨셉에 2~3개 섹터를 추천하세요.\n"
        f"- 각 섹터에 대표 종목 2~3개를 {code_rule}+이름+선정사유와 함께 제시하세요.\n"
        "- **모멘텀은 반드시 섹터 ETF 수익률 데이터 기반으로 판단하세요.** "
        "1M/3M 수익률이 높은 섹터가 모멘텀입니다. 뉴스 감성이 아닌 실제 가격 추세가 기준입니다.\n"
        "- **역발상은 1M/3M 수익률이 음수이거나 하위권인 섹터 중** 펀더멘털 반등 잠재력이 있는 섹터입니다.\n"
        "- 3개월 선점은 정책/실적/이벤트 기반 선제 포지셔닝으로, 현재 수익률과 무관하게 촉매가 예상되는 섹터입니다.\n"
        "- 추천 근거에 반드시 섹터 ETF 수익률 수치를 인용하세요.\n"
        "- JSON으로만 응답하세요.\n"
    )


def _build_user_prompt(
    regime_data: dict,
    indices_data: dict,
    news_data: dict,
    market: str,
    sector_returns: Optional[list[dict]] = None,
) -> str:
    from datetime import datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    today = datetime.now(KST).strftime("%Y-%m-%d")

    regime = regime_data.get("regime", "unknown")
    regime_desc = regime_data.get("regime_desc", regime)
    vix = regime_data.get("vix")
    buffett = regime_data.get("buffett_ratio")
    fg_score = regime_data.get("fear_greed_score")

    # 지수 정보
    indices_lines = []
    for idx in (indices_data.get("indices") or []):
        name = idx.get("name", "")
        price = idx.get("price")
        pct = idx.get("change_pct")
        if price is not None:
            indices_lines.append(f"- {name}: {price:,.1f} ({pct:+.1f}%)" if pct else f"- {name}: {price:,.1f}")

    # 섹터 ETF 수익률 테이블
    sector_lines = []
    if sector_returns:
        sector_lines.append("| 섹터 | 1M수익률 | 3M수익률 | 6M수익률 | 1Y수익률 |")
        sector_lines.append("|------|---------|---------|---------|---------|")
        for s in sector_returns:
            name_ko = s.get("name_ko", s.get("name", ""))
            r1m = f"{s['return_1m']:+.1f}%" if s.get("return_1m") is not None else "N/A"
            r3m = f"{s['return_3m']:+.1f}%" if s.get("return_3m") is not None else "N/A"
            r6m = f"{s['return_6m']:+.1f}%" if s.get("return_6m") is not None else "N/A"
            r1y = f"{s['return_1y']:+.1f}%" if s.get("return_1y") is not None else "N/A"
            sector_lines.append(f"| {name_ko} | {r1m} | {r3m} | {r6m} | {r1y} |")

    # 뉴스 헤드라인 (한국+해외 합산, 최신 10개)
    headlines = []
    for n in (news_data.get("korean") or [])[:7]:
        headlines.append(n.get("title", ""))
    for n in (news_data.get("international") or [])[:5]:
        title = n.get("title_ko") or n.get("title_original", "")
        if title:
            headlines.append(title)
    headlines = headlines[:10]

    parts = [
        f"# 시장 현황 ({today}, {market})\n",
        f"## 시장 체제\n"
        f"- 체제: {regime} ({regime_desc})\n"
        f"- VIX: {vix}\n"
        f"- 버핏지수: {buffett}\n"
        f"- 공포탐욕지수: {fg_score}\n",
        f"## 주요 지수\n"
        f"{chr(10).join(indices_lines) or '데이터 없음'}\n",
    ]

    if sector_lines:
        parts.append(
            f"## 섹터 ETF 수익률 (모멘텀/역발상 판단의 핵심 근거)\n"
            f"{chr(10).join(sector_lines)}\n\n"
            f"**해석 가이드**: 1M/3M 수익률 상위 = 모멘텀 후보, 1M/3M 수익률 하위(음수) = 역발상 후보\n"
        )

    parts.append(
        f"## 주요 뉴스 헤드라인\n"
        f"{chr(10).join(f'- {h}' for h in headlines) or '- 데이터 없음'}\n\n"
        "위 현황과 **섹터 ETF 수익률 데이터**를 분석하여 3가지 컨셉(momentum/contrarian/forward_3m)의 "
        "탑픽 섹터를 아래 JSON 형식으로 추천해주세요:\n"
        '{\n'
        '  "concepts": [\n'
        '    {\n'
        '      "concept": "momentum",\n'
        '      "concept_label": "모멘텀",\n'
        '      "description": "현재 강한 업종 1문장 요약",\n'
        '      "sectors": [\n'
        '        {\n'
        '          "sector_name": "섹터명",\n'
        '          "rationale": "추천 근거 2~3문장 (섹터 ETF 수익률 수치 인용 필수)",\n'
        '          "stocks": [\n'
        '            {"code": "종목코드", "name": "종목명", "reason": "선정 사유 1문장"}\n'
        '          ]\n'
        '        }\n'
        '      ]\n'
        '    },\n'
        '    {"concept": "contrarian", "concept_label": "역발상", ...},\n'
        '    {"concept": "forward_3m", "concept_label": "3개월 선점", ...}\n'
        '  ]\n'
        '}'
    )

    return "\n".join(parts)


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    """OpenAI GPT 호출. JSON 응답 파싱. 토큰 잘림 시 1회 재시도."""
    from services.ai_gateway import call_openai_chat

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for attempt, max_tokens in enumerate([5000, 8000]):
        resp = call_openai_chat(
            messages,
            user_id=None,  # 시스템/파이프라인 호출
            service_name="sector_recommendation",
            check_quota=(attempt == 0),
            max_completion_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        finish = resp.choices[0].finish_reason or "stop"

        if finish == "length" and attempt == 0:
            logger.warning("섹터 추천 토큰 잘림, %d 토큰으로 재시도", 8000)
            continue

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.error("섹터 추천 JSON 파싱 실패 (attempt %d): %s", attempt, content[:200])
            if attempt == 0:
                continue
            return {"concepts": []}

    return {"concepts": []}

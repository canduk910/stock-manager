"""GPT 기반 섹터 추천 서비스.

매크로 현황(체제/VIX/버핏/공포탐욕/지수/뉴스)을 입력으로
3가지 컨셉(모멘텀/역발상/3개월선점)의 탑픽 섹터를 추천한다.

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
) -> dict:
    """GPT 기반 3컨셉 섹터 추천. macro_store 일일 캐싱.

    Args:
        regime_data: determine_regime() 반환값 (regime, vix, buffett_ratio, ...)
        indices_data: macro_service.get_indices() 반환값
        news_data: macro_service.get_news() 반환값
        market: "KR" | "US"

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
    user_prompt = _build_user_prompt(regime_data, indices_data, news_data, market)

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
        "- 추천 근거는 제공된 매크로 데이터와 연결하여 구체적으로 서술하세요.\n"
        "- defensive 체제일 경우: 모멘텀 대신 방어적 섹터(헬스케어/필수소비재/유틸리티), "
        "역발상은 급락 과매도 섹터, 3개월 선점은 정부 정책/규제 완화 수혜 섹터를 추천.\n"
        "- JSON으로만 응답하세요.\n"
    )


def _build_user_prompt(
    regime_data: dict,
    indices_data: dict,
    news_data: dict,
    market: str,
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

    # 뉴스 헤드라인 (한국+해외 합산, 최신 10개)
    headlines = []
    for n in (news_data.get("korean") or [])[:7]:
        headlines.append(n.get("title", ""))
    for n in (news_data.get("international") or [])[:5]:
        title = n.get("title_ko") or n.get("title_original", "")
        if title:
            headlines.append(title)
    headlines = headlines[:10]

    return (
        f"# 시장 현황 ({today}, {market})\n\n"
        f"## 시장 체제\n"
        f"- 체제: {regime} ({regime_desc})\n"
        f"- VIX: {vix}\n"
        f"- 버핏지수: {buffett}\n"
        f"- 공포탐욕지수: {fg_score}\n\n"
        f"## 주요 지수\n"
        f"{chr(10).join(indices_lines) or '데이터 없음'}\n\n"
        f"## 주요 뉴스 헤드라인\n"
        f"{chr(10).join(f'- {h}' for h in headlines) or '- 데이터 없음'}\n\n"
        "위 현황을 분석하여 3가지 컨셉(momentum/contrarian/forward_3m)의 "
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
        '          "rationale": "추천 근거 2~3문장 (매크로 데이터 연결)",\n'
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


def _call_openai(system_prompt: str, user_prompt: str) -> dict:
    """OpenAI GPT 호출. JSON 응답 파싱. 토큰 잘림 시 1회 재시도."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    for attempt, max_tokens in enumerate([5000, 8000]):
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
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

"""매크로 분석 서비스 레이어.

데이터 수집(macro_fetcher) + OpenAI 번역/추출 + 캐싱 오케스트레이션.
수익률곡선, 신용스프레드, 환율, 원자재, 섹터 히트맵, 경기사이클 판단.
"""
from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from stock.db_base import now_kst_iso
from typing import Optional

from config import OPENAI_API_KEY, OPENAI_MODEL
from stock import macro_fetcher
from stock.macro_store import get_today as get_macro_today, save_today as save_macro_today
from services.exceptions import ExternalAPIError, PaymentRequiredError
from services.macro_cycle import determine_cycle_phase
from services.macro_regime import determine_regime

logger = logging.getLogger(__name__)


# ── 지수 ─────────────────────────────────────────────────────────────────────

def get_indices() -> dict:
    """4대 지수 현재가 + 스파크라인. 병렬 수집."""
    results = []
    now = now_kst_iso()

    with ThreadPoolExecutor(max_workers=8) as pool:
        q_futures = {}
        s_futures = {}
        for idx in macro_fetcher.INDICES:
            sym = idx["symbol"]
            q_futures[pool.submit(macro_fetcher.fetch_index_quote, sym)] = sym
            s_futures[pool.submit(macro_fetcher.fetch_index_sparkline, sym)] = sym

        quotes = {}
        for fut in as_completed(q_futures):
            sym = q_futures[fut]
            try:
                quotes[sym] = fut.result()
            except Exception:
                quotes[sym] = None

        sparklines = {}
        for fut in as_completed(s_futures):
            sym = s_futures[fut]
            try:
                sparklines[sym] = fut.result()
            except Exception:
                sparklines[sym] = []

    for idx in macro_fetcher.INDICES:
        sym = idx["symbol"]
        quote = quotes.get(sym)
        spark = sparklines.get(sym, [])

        entry = {
            "symbol": sym,
            "name": idx["name"],
            "price": quote["price"] if quote else None,
            "prev_close": quote["prev_close"] if quote else None,
            "change": quote["change"] if quote else None,
            "change_pct": quote["change_pct"] if quote else None,
            "sparkline": spark,
            "updated_at": now,
        }
        results.append(entry)

    return {"indices": results}


# ── 뉴스 ─────────────────────────────────────────────────────────────────────

def get_news() -> dict:
    """네이버 + NYT 뉴스. NYT는 GPT 번역 (키 있을 때)."""
    errors = []

    # 네이버 (한국어)
    try:
        korean = macro_fetcher.fetch_naver_news()
    except Exception as e:
        korean = []
        errors.append(f"한국 뉴스: {e}")

    # NYT (영어 → 한국어 번역)
    try:
        nyt_raw = macro_fetcher.fetch_nyt_news()
    except Exception as e:
        nyt_raw = []
        errors.append(f"NYT 뉴스: {e}")

    international = []
    if nyt_raw:
        translated_map = _translate_headlines(
            [a["title"] for a in nyt_raw],
            [a.get("summary", "") for a in nyt_raw],
        )
        for i, article in enumerate(nyt_raw):
            tr = translated_map.get(i, {})
            international.append({
                "title_original": article["title"],
                "title_ko": tr.get("title", article["title"]),
                "summary_ko": tr.get("summary", ""),
                "link": article["link"],
                "source": article.get("source") or "NYT",
                "published": article.get("published", ""),
                "translated": bool(tr.get("title")),
            })

    return {"korean": korean, "international": international, "errors": errors}


# ── 심리 지표 ────────────────────────────────────────────────────────────────

def get_sentiment() -> dict:
    """VIX + 버핏지수 + 공포탐욕 종합."""
    errors = []

    vix = None
    try:
        vix = macro_fetcher.fetch_vix()
    except Exception as e:
        errors.append(f"VIX: {e}")

    buffett = None
    try:
        buffett = macro_fetcher.calc_buffett_indicator()
    except Exception as e:
        errors.append(f"버핏지수: {e}")

    fear_greed = None
    try:
        fear_greed = macro_fetcher.calc_fear_greed()
    except Exception as e:
        errors.append(f"공포탐욕: {e}")

    now = now_kst_iso()
    return {
        "vix": vix,
        "buffett_indicator": buffett,
        "fear_greed": fear_greed,
        "updated_at": now,
        "errors": errors,
    }


# ── 투자자 코멘트 ────────────────────────────────────────────────────────────

def get_investor_quotes() -> dict:
    """투자 대가 뉴스 검색 + GPT 추출/번역."""
    investors_result = []
    errors = []

    for inv in macro_fetcher.INVESTORS:
        try:
            articles = macro_fetcher.fetch_investor_news(inv["query"])
            quotes = _extract_investor_opinions(inv["name"], inv["name_ko"], articles)
            investors_result.append({
                "name": inv["name"],
                "name_ko": inv["name_ko"],
                "quotes": quotes,
            })
        except Exception as e:
            logger.warning("투자자 코멘트 수집 실패 (%s): %s", inv["name"], e)
            investors_result.append({
                "name": inv["name"],
                "name_ko": inv["name_ko"],
                "quotes": [],
            })
            errors.append(f"{inv['name_ko']}: {e}")

    return {"investors": investors_result, "errors": errors}


# ── 수익률곡선 ──────────────────────────────────────────────────────────────

def get_yield_curve() -> dict:
    """미국 국채 수익률곡선 — 현재값 + 시계열 + 역전 여부."""
    errors = []
    now = now_kst_iso()

    data = None
    try:
        data = macro_fetcher.fetch_yield_curve_data()
    except Exception as e:
        errors.append(f"수익률곡선: {e}")

    return {
        "yield_curve": data,
        "updated_at": now,
        "errors": errors,
    }


# ── 신용스프레드 ────────────────────────────────────────────────────────────

def get_credit_spread() -> dict:
    """HYG/LQD 기반 하이일드 신용스프레드."""
    errors = []
    now = now_kst_iso()

    data = None
    try:
        data = macro_fetcher.fetch_credit_spread()
    except Exception as e:
        errors.append(f"신용스프레드: {e}")

    return {
        "credit_spread": data,
        "updated_at": now,
        "errors": errors,
    }


# ── 환율 ────────────────────────────────────────────────────────────────────

def get_currencies() -> dict:
    """주요 환율 현재가 + 스파크라인. 병렬 수집."""
    errors = []
    now = now_kst_iso()

    currencies = []
    try:
        currencies = macro_fetcher.fetch_currency_quotes()
    except Exception as e:
        errors.append(f"환율: {e}")

    return {
        "currencies": currencies,
        "updated_at": now,
        "errors": errors,
    }


# ── 원자재 ──────────────────────────────────────────────────────────────────

def get_commodities() -> dict:
    """주요 원자재 현재가 + 스파크라인. 병렬 수집."""
    errors = []
    now = now_kst_iso()

    commodities = []
    try:
        commodities = macro_fetcher.fetch_commodity_quotes()
    except Exception as e:
        errors.append(f"원자재: {e}")

    return {
        "commodities": commodities,
        "updated_at": now,
        "errors": errors,
    }


# ── 섹터 히트맵 ─────────────────────────────────────────────────────────────

def get_sector_heatmap() -> dict:
    """11개 섹터 ETF 기간별 수익률 히트맵."""
    errors = []
    now = now_kst_iso()

    sectors = []
    try:
        sectors = macro_fetcher.fetch_sector_returns()
    except Exception as e:
        errors.append(f"섹터 수익률: {e}")

    return {
        "sectors": sectors,
        "updated_at": now,
        "errors": errors,
    }


# ── 매크로 사이클 ───────────────────────────────────────────────────────────

def get_macro_cycle() -> dict:
    """경기 사이클 국면 판단 (5지표 가중합산) + 투자 체제 판단."""
    errors = []
    now = now_kst_iso()

    cycle = None
    try:
        inputs = macro_fetcher.fetch_cycle_inputs()
        cycle = determine_cycle_phase(inputs)
    except Exception as e:
        errors.append(f"경기사이클: {e}")

    regime = None
    try:
        sentiment = get_sentiment()
        regime = determine_regime(sentiment)
    except Exception as e:
        errors.append(f"투자체제: {e}")

    return {
        "cycle": cycle,
        "regime": regime,
        "updated_at": now,
        "errors": errors,
    }


# ── 통합 ─────────────────────────────────────────────────────────────────────

def get_summary() -> dict:
    """전체 섹션 통합. 각 섹션 독립 — 부분 실패 허용."""
    result = {
        "indices": None,
        "news": None,
        "sentiment": None,
        "investors": None,
        "yield_curve": None,
        "credit_spread": None,
        "currencies": None,
        "commodities": None,
        "sector_heatmap": None,
        "macro_cycle": None,
        "errors": [],
    }

    try:
        result["indices"] = get_indices()
    except Exception as e:
        result["errors"].append({"section": "indices", "message": str(e)})

    try:
        result["news"] = get_news()
    except Exception as e:
        result["errors"].append({"section": "news", "message": str(e)})

    try:
        result["sentiment"] = get_sentiment()
    except Exception as e:
        result["errors"].append({"section": "sentiment", "message": str(e)})

    try:
        result["investors"] = get_investor_quotes()
    except Exception as e:
        result["errors"].append({"section": "investors", "message": str(e)})

    try:
        result["yield_curve"] = get_yield_curve()
    except Exception as e:
        result["errors"].append({"section": "yield_curve", "message": str(e)})

    try:
        result["credit_spread"] = get_credit_spread()
    except Exception as e:
        result["errors"].append({"section": "credit_spread", "message": str(e)})

    try:
        result["currencies"] = get_currencies()
    except Exception as e:
        result["errors"].append({"section": "currencies", "message": str(e)})

    try:
        result["commodities"] = get_commodities()
    except Exception as e:
        result["errors"].append({"section": "commodities", "message": str(e)})

    try:
        result["sector_heatmap"] = get_sector_heatmap()
    except Exception as e:
        result["errors"].append({"section": "sector_heatmap", "message": str(e)})

    try:
        result["macro_cycle"] = get_macro_cycle()
    except Exception as e:
        result["errors"].append({"section": "macro_cycle", "message": str(e)})

    return result


# ── GPT 헬퍼 ─────────────────────────────────────────────────────────────────

def _translate_headlines(
    titles: list[str],
    summaries: list[str] | None = None,
) -> dict[int, dict]:
    """영문 헤드라인 배치 한국어 번역. 반환: {index: {title, summary}}."""
    if not titles:
        return {}
    if not OPENAI_API_KEY:
        return {}

    # 당일(KST) GPT 결과 재사용
    cached = get_macro_today("nyt_translation")
    if cached is not None:
        return {int(k): v for k, v in cached.items()} if isinstance(cached, dict) else {}

    summaries = summaries or [""] * len(titles)
    lines = []
    for i, (t, s) in enumerate(zip(titles, summaries)):
        lines.append(f"{i}. 제목: {t}")
        if s:
            lines.append(f"   요약: {s}")

    prompt = (
        "다음 영어 뉴스 헤드라인과 요약을 자연스러운 한국어로 번역해주세요.\n"
        "JSON 형식으로 반환: {\"0\": {\"title\": \"번역제목\", \"summary\": \"번역요약\"}, ...}\n"
        "요약이 없으면 summary는 빈 문자열로.\n\n"
        + "\n".join(lines)
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "뉴스 헤드라인 한국어 번역기. JSON으로만 응답."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=800,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
        result = {int(k): v for k, v in parsed.items() if isinstance(v, dict)}
        save_macro_today("nyt_translation", parsed)
        return result
    except Exception as e:
        _handle_openai_error(e)
        return {}


def _extract_investor_opinions(
    name: str, name_ko: str, articles: list[dict],
) -> list[dict]:
    """GPT로 투자자 코멘트 추출 + 한국어 번역."""
    if not articles:
        return []

    # 당일(KST) GPT 결과 재사용
    category = f"investor:{name}"
    cached = get_macro_today(category)
    if cached is not None:
        return cached

    if not OPENAI_API_KEY:
        # GPT 없으면 원문 제목만 반환
        return [
            {
                "text_ko": a["title"],
                "text_original": a["title"],
                "source": a.get("source", ""),
                "source_url": a.get("link", ""),
                "date": a.get("published", ""),
            }
            for a in articles[:5]
        ]

    article_text = "\n".join(
        f"- [{a.get('published', '')}] {a['title']} (출처: {a.get('source', 'N/A')})"
        for a in articles
    )

    prompt = (
        f"다음은 {name} ({name_ko})에 관한 최근 뉴스 헤드라인입니다.\n\n"
        f"{article_text}\n\n"
        "이 헤드라인들에서 해당 투자자의 시장 관련 발언이나 의견을 추출하세요.\n"
        "발언이 없으면 뉴스 내용을 간결하게 요약하세요.\n"
        "JSON: {\"quotes\": [{\"text_ko\": \"한국어 번역\", \"text_original\": \"원문\", "
        "\"source\": \"출처\", \"date\": \"날짜\"}]}\n"
        "최대 5개."
    )

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "투자 전문가 발언 추출/번역기. JSON으로만 응답."},
                {"role": "user", "content": prompt},
            ],
            max_completion_tokens=1000,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
        quotes = parsed.get("quotes", [])

        # source_url 보충
        for q in quotes:
            if not q.get("source_url"):
                # 매칭되는 기사 찾기
                for a in articles:
                    if q.get("source") and q["source"] in (a.get("source", "")):
                        q["source_url"] = a.get("link", "")
                        break
                else:
                    q["source_url"] = articles[0].get("link", "") if articles else ""

        save_macro_today(category, quotes)
        return quotes
    except Exception as e:
        _handle_openai_error(e)
        return [
            {
                "text_ko": a["title"],
                "text_original": a["title"],
                "source": a.get("source", ""),
                "source_url": a.get("link", ""),
                "date": a.get("published", ""),
            }
            for a in articles[:5]
        ]


def _handle_openai_error(e: Exception) -> None:
    """OpenAI 에러 로깅 (번역 실패는 치명적이지 않으므로 raise 안 함)."""
    err_str = str(e)
    if "insufficient_quota" in err_str or "429" in err_str:
        logger.warning("OpenAI 크레딧 부족: %s", err_str)
    else:
        logger.warning("OpenAI 호출 실패: %s", err_str)

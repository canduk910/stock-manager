"""리서치 데이터 수집 모듈 — AI분석 입력정보 5카테고리.

LLM 비용 없이 무료 API/크롤링으로 데이터를 수집한다.
각 카테고리는 독립적으로 실패할 수 있으며, 부분 수집도 허용한다.

카테고리:
  1. 기본 및 거시 지표 (종목명/시가총액/원자재/환율/금리)
  2. 역사적 밸류에이션 (10년 PER/PBR 밴드 + 실적 발표일 반응)
  3. 경영진 및 거버넌스 (CEO/CFO + 주요주주 + 기관투자자)
  4. 자본 변동 및 공시 (CB/BW/자사주 + 최근 공시)
  5. 업황 및 경쟁 그룹 (뉴스 + 경쟁사 밸류에이션)

Note: 재무 및 실적 카테고리는 advisory_service._collect_fundamental에서
      10년 데이터를 직접 수집하므로 여기서는 제외.
"""

from __future__ import annotations

import logging
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def collect_all_research(code: str, market: str, name: str) -> dict:
    """5카테고리 리서치 데이터 병렬 수집.

    각 카테고리는 독립 실패 허용. 에러 발생 시 해당 카테고리만 빈 dict/list로 처리.
    반환: {basic_macro, valuation_band, management,
           capital_actions, industry_peers, collected_at, categories_ok}

    Note: financial_history는 advisory_service._collect_fundamental에서
          10년 데이터를 직접 수집하므로 제외.
    """
    tasks = {
        "basic_macro": (_collect_basic_macro, (code, market, name)),
        "valuation_band": (_collect_valuation_band, (code, market)),
        "management": (_collect_management, (code, market)),
        "capital_actions": (_collect_capital_actions, (code, market, name)),
        "industry_peers": (_collect_industry_peers, (code, market, name)),
    }

    result = {}
    categories_ok = 0

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {}
        for cat_name, (fn, args) in tasks.items():
            futures[pool.submit(fn, *args)] = cat_name

        for future in as_completed(futures):
            cat_name = futures[future]
            try:
                data = future.result()
                result[cat_name] = data
                if data:
                    categories_ok += 1
            except Exception as e:
                logger.warning("리서치 %s 수집 실패: %s", cat_name, e)
                result[cat_name] = {}

    from db.utils import now_kst_iso
    result["collected_at"] = now_kst_iso()
    result["categories_ok"] = categories_ok
    return result


# ── 카테고리 1: 기본 및 거시 지표 ────────────────────────────────────────────────


def _collect_basic_macro(code: str, market: str, name: str) -> dict:
    """종목 기본정보 + 거시경제 지표."""
    from stock import market as mkt_mod
    from stock import yf_client

    result = {}

    # 현재가 + 시가총액 + 섹터
    try:
        metrics = mkt_mod.fetch_market_metrics(code)
        result["current_price"] = mkt_mod.fetch_price(code)
        result["market_cap"] = metrics.get("mktcap")
        result["sector"] = metrics.get("sector")
        result["per"] = metrics.get("per")
        result["pbr"] = metrics.get("pbr")
        result["roe"] = metrics.get("roe")
        result["dividend_yield"] = metrics.get("dividend_yield")
        result["high_52"] = metrics.get("high_52")
        result["low_52"] = metrics.get("low_52")
    except Exception as e:
        logger.warning("기본 지표 수집 실패 %s: %s", code, e)

    # 거시 지표
    try:
        macro = yf_client.fetch_macro_indicators()
        result["macro"] = macro
    except Exception as e:
        logger.warning("거시 지표 수집 실패: %s", e)
        result["macro"] = {}

    result["name"] = name
    result["code"] = code
    result["market"] = market
    return result


# ── 카테고리 2: 역사적 밸류에이션 ────────────────────────────────────────────────


def _collect_valuation_band(code: str, market: str) -> dict:
    """10년 PER/PBR 밴드 + 실적 발표일 반응."""
    from stock import yf_client
    from stock import advisory_fetcher

    result = {"valuation_history": [], "valuation_stats": {},
              "earnings_dates": []}

    # 10년 PER/PBR 월별 히스토리
    try:
        result["valuation_history"] = yf_client.fetch_valuation_history_yf(code, years=10)
    except Exception as e:
        logger.warning("밸류에이션 히스토리 수집 실패 %s: %s", code, e)

    # PER/PBR 통계 (10년)
    try:
        result["valuation_stats"] = advisory_fetcher.fetch_valuation_stats(code, market)
    except Exception as e:
        logger.warning("밸류에이션 통계 수집 실패 %s: %s", code, e)

    # 실적 발표일 + EPS surprise
    try:
        result["earnings_dates"] = yf_client.fetch_earnings_dates(code, limit=12)
    except Exception as e:
        logger.warning("실적 발표일 수집 실패 %s: %s", code, e)

    return result


# ── 카테고리 3: 경영진 및 거버넌스 ───────────────────────────────────────────────


def _collect_management(code: str, market: str) -> dict:
    """경영진 정보 + 주요 주주."""
    from stock import yf_client
    from stock.utils import is_domestic

    result = {"officers": [], "major_holders": {"summary": [], "institutional": []}}

    ticker_code = code
    if is_domestic(code):
        # 국내 종목은 yfinance suffix 추가
        from stock.market import _kr_yf_ticker_str
        try:
            ticker_code = _kr_yf_ticker_str(code)
        except Exception:
            ticker_code = f"{code}.KS"

    try:
        result["officers"] = yf_client.fetch_company_officers(ticker_code)
    except Exception as e:
        logger.warning("경영진 수집 실패 %s: %s", code, e)

    try:
        result["major_holders"] = yf_client.fetch_major_holders(ticker_code)
    except Exception as e:
        logger.warning("주요주주 수집 실패 %s: %s", code, e)

    return result


# ── 카테고리 4: 자본 변동 및 공시 ────────────────────────────────────────────────


def _collect_capital_actions(code: str, market: str, name: str) -> dict:
    """최근 1년 공시 목록 (CB/BW/자사주 포함)."""
    from stock.utils import is_domestic

    result = {"filings": []}

    end_date = date.today().strftime("%Y%m%d")
    start_date = (date.today() - timedelta(days=365)).strftime("%Y%m%d")

    if is_domestic(code):
        try:
            from screener.dart import fetch_filings
            all_filings = fetch_filings(start_date, end_date)
            # 해당 종목만 필터
            result["filings"] = [
                f for f in all_filings
                if f.get("stock_code") == code
            ][:20]
        except Exception as e:
            logger.warning("DART 공시 수집 실패 %s: %s", code, e)
    else:
        try:
            from stock.sec_filings import fetch_sec_filings
            all_filings = fetch_sec_filings(start_date, end_date)
            result["filings"] = [
                f for f in all_filings
                if f.get("stock_code", "").upper() == code.upper()
            ][:20]
        except Exception as e:
            logger.warning("SEC 공시 수집 실패 %s: %s", code, e)

    return result


# ── 카테고리 5: 업황 및 경쟁 그룹 ────────────────────────────────────────────────


_GOOGLE_NEWS_KR_RSS = "https://news.google.com/rss/search?hl=ko&gl=KR&ceid=KR:ko&q={query}"
_GOOGLE_NEWS_US_RSS = "https://news.google.com/rss/search?hl=en&gl=US&ceid=US:en&q={query}"


def _collect_industry_peers(code: str, market: str, name: str) -> dict:
    """업종 뉴스 + 경쟁사 밸류에이션."""
    from stock.utils import is_domestic

    result = {"news": [], "peers": [], "sector": "", "industry": ""}

    # 뉴스 수집
    try:
        result["news"] = _fetch_stock_news(name, market)
    except Exception as e:
        logger.warning("뉴스 수집 실패 %s: %s", name, e)

    # 섹터/경쟁사 정보
    try:
        from stock import yf_client

        ticker_code = code
        if is_domestic(code):
            from stock.market import _kr_yf_ticker_str
            try:
                ticker_code = _kr_yf_ticker_str(code)
            except Exception:
                ticker_code = f"{code}.KS"

        peer_info = yf_client.fetch_sector_peers(ticker_code)
        result["sector"] = peer_info.get("sector", "")
        result["industry"] = peer_info.get("industry", "")
        result["peers"] = peer_info.get("peers", [])
    except Exception as e:
        logger.warning("섹터/경쟁사 수집 실패 %s: %s", code, e)

    return result


def _fetch_stock_news(name: str, market: str, max_items: int = 10) -> list[dict]:
    """종목명 기반 Google News RSS 크롤링."""
    import re

    query = f'"{name}" 주식 OR 실적' if market == "KR" else f'"{name}" stock OR earnings'
    slug = urllib.parse.quote_plus(query)

    rss_url = (_GOOGLE_NEWS_KR_RSS if market == "KR" else _GOOGLE_NEWS_US_RSS).format(query=slug)

    try:
        import feedparser
        feed = feedparser.parse(rss_url)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "")
            # HTML 태그 제거
            title = re.sub(r"<[^>]+>", "", title)
            published = getattr(entry, "published", "") or getattr(entry, "updated", "")
            source = ""
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source = entry.source.title
            items.append({
                "title": title,
                "link": entry.get("link", ""),
                "source": source,
                "published": published,
            })
        return items
    except Exception as e:
        logger.warning("RSS 뉴스 수집 실패: %s", e)
        return []

"""리서치 데이터 수집 모듈 — AI분석 입력정보 6카테고리.

LLM 비용 없이 무료 API/크롤링으로 데이터를 수집한다.
각 카테고리는 독립적으로 실패할 수 있으며, 부분 수집도 허용한다.

카테고리:
  1. 기본 및 거시 지표 (종목명/시가총액/원자재/환율/금리)
  2. 역사적 밸류에이션 (10년 PER/PBR 밴드 + 실적 발표일 반응)
  3. 경영진 및 거버넌스 (CEO/CFO + 주요주주 + 기관투자자)
  4. 자본 변동 및 공시 (CB/BW/자사주 + 최근 공시)
  5. 업황 및 경쟁 그룹 (뉴스 + 경쟁사 밸류에이션)
  6. 증권사 컨센서스 (목표가 + PDF 본문 요약 + 시간축 추이) — REQ-ANALYST-07

Note: 재무 및 실적 카테고리는 advisory_service._collect_fundamental에서
      10년 데이터를 직접 수집하므로 여기서는 제외.
"""

from __future__ import annotations

import logging
import math
import statistics
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def collect_all_research(code: str, market: str, name: str) -> dict:
    """6카테고리 리서치 데이터 병렬 수집.

    각 카테고리는 독립 실패 허용. 에러 발생 시 해당 카테고리만 빈 dict/list로 처리.
    반환: {basic_macro, valuation_band, management,
           capital_actions, industry_peers, analyst_consensus,
           collected_at, categories_ok}

    Note: financial_history는 advisory_service._collect_fundamental에서
          10년 데이터를 직접 수집하므로 제외.
    """
    tasks = {
        "basic_macro": (_collect_basic_macro, (code, market, name)),
        "valuation_band": (_collect_valuation_band, (code, market)),
        "management": (_collect_management, (code, market)),
        "capital_actions": (_collect_capital_actions, (code, market, name)),
        "industry_peers": (_collect_industry_peers, (code, market, name)),
        "analyst_consensus": (_collect_analyst_consensus, (code, market, name)),
    }

    result = {}
    categories_ok = 0

    with ThreadPoolExecutor(max_workers=6) as pool:
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


# ── 카테고리 6: 증권사 컨센서스 (REQ-ANALYST-07) ──────────────────────────────

# 의견 매핑 — 5단계 원본 ↔ 3단계 정규화 (REQ-ANALYST-04)
_OPINION_5_MAP = {
    # strong_buy
    "Strong Buy": "strong_buy",
    "강력매수": "strong_buy",
    "BUY": "strong_buy",
    # buy
    "Buy": "buy",
    "매수": "buy",
    "Outperform": "buy",
    "Overweight": "buy",
    "Accumulate": "buy",
    # hold
    "Hold": "hold",
    "Neutral": "hold",
    "보유": "hold",
    "관망": "hold",
    "Equal-Weight": "hold",
    "Equal Weight": "hold",
    "Sector Perform": "hold",
    "Market Perform": "hold",
    # sell
    "Sell": "sell",
    "Underperform": "sell",
    "Underweight": "sell",
    "매도": "sell",
    "Reduce": "sell",
    # strong_sell
    "Strong Sell": "strong_sell",
    "강력매도": "strong_sell",
}

_FIVE_TO_THREE = {
    "strong_buy": "buy",
    "buy": "buy",
    "hold": "hold",
    "sell": "sell",
    "strong_sell": "sell",
}


def _normalize_opinion_5(raw: str | None) -> str:
    """원본 의견 라벨 → 5단계 정규화. 매핑 불가 → 'hold' (보수적)."""
    if not raw:
        return "hold"
    s = raw.strip()
    return _OPINION_5_MAP.get(s, "hold")


def _compute_consensus(reports: list[dict], current_price: float | None) -> dict:
    """REQ-ANALYST-04: 컨센서스 통계 (중앙값 우선).

    target_price=None 행은 통계 분모에서 제외, count는 전체.
    의견 매핑 불가 라벨 → hold로 간주.
    """
    count = len(reports)
    if count == 0:
        return {
            "target_median": None, "target_mean": None,
            "target_stdev": None, "target_dispersion": None,
            "upside_pct_median": None,
            "opinion_dist_3": {"buy": 0, "hold": 0, "sell": 0},
            "opinion_dist_raw": {
                "strong_buy": 0, "buy": 0, "hold": 0,
                "sell": 0, "strong_sell": 0,
            },
            "count": 0,
        }

    # target_price 통계 (None 제외)
    targets = [
        r["target_price"] for r in reports
        if r.get("target_price") is not None
    ]
    if targets:
        try:
            target_median = float(statistics.median(targets))
            target_mean = float(statistics.fmean(targets))
            target_stdev = (
                float(statistics.pstdev(targets)) if len(targets) >= 2 else 0.0
            )
            dispersion = (
                round(target_stdev / target_median, 2)
                if target_median and not math.isclose(target_median, 0)
                else None
            )
            upside = None
            if current_price and current_price > 0 and target_median:
                upside = round(
                    (target_median - current_price) / current_price * 100, 2
                )
            # KR 정수 변환 (target_price가 모두 int면 int 유지)
            if all(isinstance(t, int) for t in targets):
                target_median = int(round(target_median))
                target_mean = int(round(target_mean))
                target_stdev = int(round(target_stdev))
        except Exception as e:
            logger.warning("컨센서스 통계 산출 실패: %s", e)
            target_median = target_mean = target_stdev = dispersion = upside = None
    else:
        target_median = target_mean = target_stdev = dispersion = upside = None

    # 의견 분포 (전체 행 포함)
    raw_dist = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0}
    for r in reports:
        five = _normalize_opinion_5(r.get("opinion"))
        raw_dist[five] = raw_dist.get(five, 0) + 1
    three_dist = {"buy": 0, "hold": 0, "sell": 0}
    for k, v in raw_dist.items():
        three_dist[_FIVE_TO_THREE[k]] += v

    return {
        "target_median": target_median,
        "target_mean": target_mean,
        "target_stdev": target_stdev,
        "target_dispersion": dispersion,
        "upside_pct_median": upside,
        "opinion_dist_3": three_dist,
        "opinion_dist_raw": raw_dist,
        "count": count,
    }


def _compute_momentum(history: list[dict]) -> tuple[str, bool]:
    """REQ-ANALYST-05: 6개월 목표가 추이 → momentum_signal + consensus_overheated.

    Args:
        history: [{"broker", "date", "target_price", "opinion"}, ...]

    Returns:
        (momentum_signal, consensus_overheated)
        signal: strong_up | up | flat | down | strong_down
        overheated: 30%+ 상향한 broker가 전체의 50% 초과면 True
    """
    # broker별로 그룹화
    by_broker: dict[str, list[dict]] = {}
    for h in history or []:
        b = h.get("broker") or ""
        if not b:
            continue
        by_broker.setdefault(b, []).append(h)

    # 각 broker의 가장 오래된 vs 가장 최신 변화율 계산
    changes: list[float] = []
    for rows in by_broker.values():
        if len(rows) < 2:
            continue
        rows_sorted = sorted(rows, key=lambda r: r.get("date") or "")
        oldest = rows_sorted[0]
        newest = rows_sorted[-1]
        old_tp = oldest.get("target_price")
        new_tp = newest.get("target_price")
        if not old_tp or old_tp <= 0 or new_tp is None:
            continue
        try:
            change = (float(new_tp) - float(old_tp)) / float(old_tp)
            changes.append(change)
        except Exception:
            continue

    if not changes:
        return "flat", False

    avg_change = sum(changes) / len(changes)

    # 5단계 라벨
    if avg_change > 0.20:
        signal = "strong_up"
    elif avg_change > 0.05:
        signal = "up"
    elif avg_change >= -0.05:
        signal = "flat"
    elif avg_change >= -0.20:
        signal = "down"
    else:
        signal = "strong_down"

    # 과열 시그널: 30%+ 상향한 broker가 전체의 50% 초과
    up_30 = sum(1 for c in changes if c >= 0.30)
    overheated = (up_30 / len(changes)) > 0.5

    return signal, overheated


def _build_history_line(history: list[dict], market: str, max_points: int = 5) -> str:
    """전체 컨센서스 중앙값 시계열 텍스트.

    history 항목들을 published_at으로 그룹화 → 그룹별 중앙값 → 최대 5개 시점 출력.
    형식: "8.5만(11/15) → 9만(2/2) → 10만(4/28)"
    """
    if not history:
        return ""

    # 날짜별 target_price 그룹화 (None 제외)
    by_date: dict[str, list[float]] = {}
    for h in history:
        tp = h.get("target_price")
        if tp is None:
            continue
        d = (h.get("date") or "")[:10]
        if not d:
            continue
        by_date.setdefault(d, []).append(float(tp))

    if not by_date:
        return ""

    # 시간순 정렬 → 균등 샘플링 (max_points)
    dates_sorted = sorted(by_date.keys())
    if len(dates_sorted) > max_points:
        step = len(dates_sorted) / max_points
        idxs = [int(i * step) for i in range(max_points)]
        if idxs[-1] != len(dates_sorted) - 1:
            idxs[-1] = len(dates_sorted) - 1
        sampled = [dates_sorted[i] for i in idxs]
    else:
        sampled = dates_sorted

    pieces = []
    for d in sampled:
        vals = by_date[d]
        med = statistics.median(vals) if vals else 0
        # KR: 만원 단위 표기, US: $ 표기
        if market.upper() == "KR":
            label = f"{med / 10000:.1f}만"
        else:
            label = f"${med:.1f}"
        # 날짜는 MM/DD
        try:
            from datetime import date as _date
            dd = _date.fromisoformat(d)
            date_label = f"{dd.month}/{dd.day}"
        except Exception:
            date_label = d
        pieces.append(f"{label}({date_label})")

    return " → ".join(pieces)


def _collect_analyst_consensus(code: str, market: str, name: str) -> dict:
    """REQ-ANALYST-07: 6번째 카테고리 — 증권사 컨센서스.

    KR: naver_research → PDF 요약 (상위 5건) → DB upsert → 시간축 추이
    US: yfinance upgrades_downgrades → DB upsert (target_price 부재)

    반환: {reports, consensus, history_line, momentum_signal,
           consensus_overheated, data_source}
    """
    from stock.utils import is_domestic

    fallback = {
        "reports": [], "consensus": None,
        "history_line": "", "momentum_signal": "flat",
        "consensus_overheated": False,
        "data_source": "empty",
    }

    try:
        if is_domestic(code):
            return _collect_kr_analyst(code, market, name) or fallback
        else:
            return _collect_us_analyst(code, market, name) or fallback
    except Exception as e:
        logger.warning("컨센서스 수집 실패 %s: %s", code, e)
        return fallback


def _collect_kr_analyst(code: str, market: str, name: str) -> dict:
    """KR: 네이버 리서치 → PDF 요약 + DB 영속화."""
    from stock import naver_research, analyst_pdf, market as mkt_mod
    from db.repositories.analyst_repo import AnalystRepository
    from db.session import get_session

    metas = []
    try:
        metas = naver_research.fetch_analyst_reports(code, limit=20) or []
    except Exception as e:
        logger.warning("네이버 리서치 조회 실패 %s: %s", code, e)
        metas = []

    if not metas:
        return {
            "reports": [], "consensus": None,
            "history_line": "", "momentum_signal": "flat",
            "consensus_overheated": False,
            "data_source": "empty",
        }

    # 상위 5건만 PDF 처리
    top5 = metas[:5]
    enriched_reports = []
    for r in top5:
        pdf_url = r.get("pdf_url") or ""
        summary = ""
        if pdf_url:
            try:
                summary = analyst_pdf.summarize_one(pdf_url)
            except Exception as e:
                logger.debug("PDF 요약 실패 (%s): %s", pdf_url, e)
                summary = ""
        enriched_reports.append({
            "broker": r.get("broker", ""),
            "title": r.get("title", ""),
            "target_price": r.get("target_price"),
            "opinion": r.get("opinion"),
            "date": r.get("date", ""),
            "pdf_url": pdf_url,
            "summary": summary,
        })

    # 현재가 조회 (upside_pct 계산용)
    current_price = None
    try:
        current_price = mkt_mod.fetch_price(code)
    except Exception:
        pass

    # 컨센서스 통계
    consensus = _compute_consensus(enriched_reports, current_price)

    # DB 영속화: 상위 5건 (요약 포함) + 나머지 메타 (요약 없음)
    try:
        with get_session() as db:
            repo = AnalystRepository(db)
            for r in enriched_reports:
                repo.upsert_report(
                    code=code, market=market,
                    broker=r["broker"],
                    target_price=r.get("target_price"),
                    opinion=r.get("opinion"),
                    title=r.get("title", ""),
                    pdf_url=r.get("pdf_url", ""),
                    summary=r.get("summary", ""),
                    published_at=r.get("date", ""),
                )
            # 나머지 메타는 요약 없이 메타만 저장 (이력 보존)
            for r in metas[5:]:
                repo.upsert_report(
                    code=code, market=market,
                    broker=r.get("broker", ""),
                    target_price=r.get("target_price"),
                    opinion=r.get("opinion"),
                    title=r.get("title", ""),
                    pdf_url=r.get("pdf_url", ""),
                    summary="",
                    published_at=r.get("date", ""),
                )
    except Exception as e:
        logger.warning("analyst_reports DB 저장 실패 %s: %s", code, e)

    # 시간축 추이 (180일)
    history = []
    try:
        with get_session() as db:
            repo = AnalystRepository(db)
            history = repo.get_target_price_history(code, market, days=180)
    except Exception as e:
        logger.debug("시간축 조회 실패 %s: %s", code, e)
        history = []

    momentum_signal, consensus_overheated = _compute_momentum(history)
    history_line = _build_history_line(history, market)

    return {
        "reports": enriched_reports,
        "consensus": consensus,
        "history_line": history_line,
        "momentum_signal": momentum_signal,
        "consensus_overheated": consensus_overheated,
        "data_source": "naver_research",
    }


def _collect_us_analyst(code: str, market: str, name: str) -> dict:
    """US: yfinance upgrades_downgrades 메타데이터 (PDF 없음)."""
    from stock import yf_client
    from db.repositories.analyst_repo import AnalystRepository
    from db.session import get_session

    metas = []
    try:
        metas = yf_client.fetch_upgrades_downgrades(code, limit=20) or []
    except Exception as e:
        logger.warning("yf upgrades_downgrades 실패 %s: %s", code, e)
        metas = []

    if not metas:
        return {
            "reports": [], "consensus": None,
            "history_line": "", "momentum_signal": "flat",
            "consensus_overheated": False,
            "data_source": "empty",
        }

    enriched_reports = []
    for r in metas[:5]:
        # yfinance 등급 변경 → opinion = to_grade
        broker = r.get("broker", "") or r.get("firm", "")
        from_grade = r.get("from_grade", "")
        to_grade = r.get("to_grade", "")
        date_s = r.get("date", "") or r.get("published", "")
        title = f"{from_grade} → {to_grade}".strip(" →")
        enriched_reports.append({
            "broker": broker,
            "title": title or to_grade or "Grade change",
            "target_price": None,
            "opinion": to_grade or None,
            "date": date_s,
            "pdf_url": "",
            "summary": "",
        })

    current_price = None
    try:
        current_price = yf_client.fetch_price_yf(code)
    except Exception:
        pass

    consensus = _compute_consensus(enriched_reports, current_price)

    # DB 영속화
    try:
        with get_session() as db:
            repo = AnalystRepository(db)
            for r in enriched_reports:
                repo.upsert_report(
                    code=code, market=market,
                    broker=r["broker"],
                    target_price=None,
                    opinion=r.get("opinion"),
                    title=r.get("title", ""),
                    pdf_url="",
                    summary="",
                    published_at=r.get("date", ""),
                )
    except Exception as e:
        logger.warning("US analyst_reports DB 저장 실패 %s: %s", code, e)

    return {
        "reports": enriched_reports,
        "consensus": consensus,
        "history_line": "",
        "momentum_signal": "flat",
        "consensus_overheated": False,
        "data_source": "yfinance_upgrades",
    }

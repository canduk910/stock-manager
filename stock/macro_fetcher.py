"""매크로 분석 데이터 수집.

yfinance 지수 데이터, RSS 뉴스 피드, 시장심리 지표,
수익률곡선, 신용스프레드, 환율, 원자재, 섹터 수익률, 경기사이클 입력.
"""
from __future__ import annotations

import logging
import math
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from stock.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

# ── 상수 ─────────────────────────────────────────────────────────────────────

INDICES = [
    {"symbol": "^KS11", "name": "코스피"},
    {"symbol": "^KQ11", "name": "코스닥"},
    {"symbol": "^GSPC", "name": "S&P 500"},
    {"symbol": "^IXIC", "name": "나스닥"},
]

INVESTORS = [
    {"name": "Warren Buffett", "name_ko": "워렌 버핏",
     "query": '"Warren Buffett" market OR investing'},
    {"name": "Ray Dalio", "name_ko": "레이 달리오",
     "query": '"Ray Dalio" market OR economy'},
    {"name": "Howard Marks", "name_ko": "하워드 막스",
     "query": '"Howard Marks" Oaktree market'},
    {"name": "Ken Fisher", "name_ko": "켄 피셔",
     "query": '"Ken Fisher" market OR stocks'},
    {"name": "Mohnish Pabrai", "name_ko": "모니시 파브라이",
     "query": '"Mohnish Pabrai" investing OR market OR stocks'},
    {"name": "Stanley Druckenmiller", "name_ko": "스탠리 드러켄밀러",
     "query": '"Stanley Druckenmiller" market OR economy'},
]

# 한국 뉴스 — 비즈니스 토픽(화제순 큐레이션) + 시장 핵심 키워드 검색
_KR_NEWS_FEEDS = [
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtdHZHZ0pMVWlnQVAB?hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=한국+증시+금리+환율&hl=ko&gl=KR&ceid=KR:ko",
]
# 해외 뉴스 — NYT Business + Google News US 비즈니스 토픽
_INTL_NEWS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en&gl=US&ceid=US:en",
]
_GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?hl=en&gl=US&ceid=US:en&q={query}"


def _safe(v) -> Optional[float]:
    if v is None:
        return None
    try:
        fv = float(v)
        return None if (math.isnan(fv) or math.isinf(fv)) else fv
    except (TypeError, ValueError):
        return None


def _strip_html(text: str) -> str:
    """HTML 태그 제거."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


# ── 지수 ─────────────────────────────────────────────────────────────────────

def fetch_index_quote(symbol: str) -> Optional[dict]:
    """지수 현재가 + 전일대비."""
    key = f"macro:index:{symbol}"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        fi = t.fast_info

        price = _safe(fi.last_price) or _safe(fi.previous_close)
        if price is None:
            return None

        prev = _safe(fi.previous_close) or price
        change = round(price - prev, 2)
        change_pct = round((price - prev) / prev * 100, 2) if prev else 0

        result = {
            "price": round(price, 2),
            "prev_close": round(prev, 2),
            "change": change,
            "change_pct": change_pct,
        }
        set_cached(key, result, ttl_hours=0.17)  # ~10분
        return result
    except Exception as e:
        logger.warning("지수 조회 실패 (%s): %s", symbol, e)
        return None


def fetch_index_sparkline(symbol: str, period: str = "1y") -> list[dict]:
    """일봉 종가 + 날짜 리스트 (스파크라인 + 툴팁용)."""
    key = f"macro:sparkline_v2:{symbol}:{period}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        hist = t.history(period=period, interval="1d")
        if hist.empty:
            return []

        result = []
        for ts, row in hist.iterrows():
            close = _safe(row["Close"])
            if close is not None:
                result.append({
                    "date": ts.strftime("%Y-%m-%d"),
                    "v": round(close, 2),
                })
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception as e:
        logger.warning("스파크라인 조회 실패 (%s): %s", symbol, e)
        return []


# ── VIX ──────────────────────────────────────────────────────────────────────

def fetch_vix() -> Optional[dict]:
    """VIX 현재값 + 변동 + 레벨 + 1개월 스파크라인."""
    key = "macro:vix"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        import yfinance as yf
        t = yf.Ticker("^VIX")
        fi = t.fast_info

        value = _safe(fi.last_price) or _safe(fi.previous_close)
        if value is None:
            return None

        prev = _safe(fi.previous_close) or value
        change = round(value - prev, 2)

        if value < 15:
            level = "low"
        elif value < 25:
            level = "normal"
        elif value < 35:
            level = "high"
        else:
            level = "extreme"

        hist = t.history(period="1mo", interval="1d")
        sparkline = (
            [round(float(v), 2) for v in hist["Close"].dropna().tolist()]
            if not hist.empty
            else []
        )

        result = {
            "value": round(value, 2),
            "prev": round(prev, 2),
            "change": change,
            "level": level,
            "sparkline": sparkline,
        }
        set_cached(key, result, ttl_hours=0.17)
        return result
    except Exception as e:
        logger.warning("VIX 조회 실패: %s", e)
        return None


# ── 버핏 지수 ────────────────────────────────────────────────────────────────

def calc_buffett_indicator() -> Optional[dict]:
    """Buffett Indicator = US Total Market Cap / GDP (근사)."""
    key = "macro:buffett"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        import yfinance as yf

        # Wilshire 5000 으로 전체 시장 시가총액 근사
        w5 = yf.Ticker("^W5000")
        w5_fi = w5.fast_info
        w5_val = _safe(w5_fi.last_price) or _safe(w5_fi.previous_close)

        if w5_val is not None:
            market_cap_t = w5_val / 1000  # 지수 → 조 달러 근사
        else:
            # fallback: S&P 500 기반 추정
            sp = yf.Ticker("^GSPC")
            sp_val = _safe(sp.fast_info.last_price) or _safe(sp.fast_info.previous_close)
            if sp_val is None:
                return None
            market_cap_t = sp_val * 10 * 1.4 / 1000

        # US GDP 연환산 (하드코딩, 분기별 수동 업데이트)
        gdp_t = 29.0  # 2025 추정

        ratio = round(market_cap_t / gdp_t * 100, 1) if gdp_t else 0

        if ratio < 80:
            level, desc = "undervalued", "저평가"
        elif ratio < 100:
            level, desc = "fair", "적정"
        elif ratio < 130:
            level, desc = "overvalued", "고평가"
        else:
            level, desc = "significantly_overvalued", "상당히 고평가"

        result = {
            "ratio": ratio,
            "market_cap_t": round(market_cap_t, 1),
            "gdp_t": gdp_t,
            "level": level,
            "description": f"{ratio}% — {desc}",
        }
        set_cached(key, result, ttl_hours=24)
        return result
    except Exception as e:
        logger.warning("버핏지수 계산 실패: %s", e)
        return None


# ── 공포탐욕 지수 ────────────────────────────────────────────────────────────

def calc_fear_greed() -> Optional[dict]:
    """VIX + S&P 500 모멘텀 기반 공포탐욕 종합점수 (0=극공포, 100=극탐욕)."""
    key = "macro:fear_greed"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        import yfinance as yf

        # 1) VIX 점수 (VIX 낮을수록 탐욕)
        vix_val = _safe(yf.Ticker("^VIX").fast_info.last_price) or 20
        vix_score = max(0, min(100, round((40 - vix_val) / 30 * 100)))

        # 2) S&P 500 모멘텀 (현재가 vs 125일 MA)
        sp = yf.Ticker("^GSPC")
        hist = sp.history(period="6mo", interval="1d")
        if hist.empty or len(hist) < 20:
            momentum_score = 50
        else:
            closes = hist["Close"]
            current = float(closes.iloc[-1])
            ma125 = float(closes.tail(125).mean()) if len(closes) >= 125 else float(closes.mean())
            pct_diff = (current - ma125) / ma125 * 100
            momentum_score = max(0, min(100, round(50 + pct_diff * 5)))

        # 3) 시장폭 (최근 20일 양봉 비율)
        if not hist.empty and len(hist) >= 20:
            recent = hist.tail(20)
            up_days = sum(1 for _, row in recent.iterrows() if row["Close"] > row["Open"])
            breadth_score = round(up_days / 20 * 100)
        else:
            breadth_score = 50

        # 종합 (가중 평균)
        score = round(vix_score * 0.4 + momentum_score * 0.35 + breadth_score * 0.25)

        if score >= 80:
            label = "극심한 탐욕"
        elif score >= 60:
            label = "탐욕"
        elif score >= 40:
            label = "중립"
        elif score >= 20:
            label = "공포"
        else:
            label = "극심한 공포"

        result = {
            "score": score,
            "label": label,
            "components": {
                "vix_score": vix_score,
                "momentum_score": momentum_score,
                "breadth_score": breadth_score,
            },
        }
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception as e:
        logger.warning("공포탐욕지수 계산 실패: %s", e)
        return None


# ── RSS 파싱 ─────────────────────────────────────────────────────────────────

def _parse_published_ts(date_str: str) -> float:
    """RSS published 문자열 → Unix timestamp. 파싱 실패 시 0 반환."""
    if not date_str:
        return 0.0
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str).timestamp()
    except Exception:
        pass
    # feedparser의 time_struct 형태 fallback
    try:
        import time as _time
        import calendar
        tp = _time.strptime(date_str[:25], "%a, %d %b %Y %H:%M:%S")
        return float(calendar.timegm(tp))
    except Exception:
        return 0.0


def _dedup_and_sort(articles: list[dict], max_items: int) -> list[dict]:
    """제목 기반 중복 제거 + 최신순 정렬."""
    import re as _re
    seen: set[str] = set()
    unique: list[dict] = []
    for a in articles:
        # 공백/특수문자 제거한 앞 30자로 중복 판별
        key = _re.sub(r"[\s\-·:|\[\]()]+", "", a.get("title", ""))[:30]
        if key and key not in seen:
            seen.add(key)
            unique.append(a)
    unique.sort(key=lambda x: x.get("published_ts", 0), reverse=True)
    return unique[:max_items]


def _parse_rss(url: str, max_items: int = 15) -> list[dict]:
    """feedparser로 RSS 파싱. published_ts(타임스탬프) 포함."""
    try:
        import feedparser
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            published = getattr(entry, "published", "") or getattr(entry, "updated", "")
            source = ""
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                source = entry.source.title

            items.append({
                "title": _strip_html(entry.get("title", "")),
                "link": entry.get("link", ""),
                "summary": _strip_html((entry.get("summary") or ""))[:200],
                "source": source,
                "published": published,
                "published_ts": _parse_published_ts(published),
            })
        return items
    except Exception as e:
        logger.warning("RSS 파싱 실패 (%s): %s", url[:60], e)
        return []


def fetch_naver_news(max_items: int = 15) -> list[dict]:
    """한국 경제 뉴스 — 다중 토픽 + 중복 제거 + 최신순."""
    key = "macro:news:naver"
    cached = get_cached(key)
    if cached is not None:
        return cached

    all_items: list[dict] = []
    for url in _KR_NEWS_FEEDS:
        all_items.extend(_parse_rss(url, max_items=20))

    items = _dedup_and_sort(all_items, max_items)
    if items:
        set_cached(key, items, ttl_hours=0.5)
    return items


def fetch_nyt_news(max_items: int = 10) -> list[dict]:
    """해외 경제 뉴스 — NYT + Google News US 비즈니스 + 중복 제거 + 최신순."""
    key = "macro:news:nyt_raw"
    cached = get_cached(key)
    if cached is not None:
        return cached

    all_items: list[dict] = []
    for url in _INTL_NEWS_FEEDS:
        all_items.extend(_parse_rss(url, max_items=15))

    items = _dedup_and_sort(all_items, max_items)
    if items:
        set_cached(key, items, ttl_hours=0.5)
    return items


def fetch_investor_news(query: str, max_items: int = 5) -> list[dict]:
    """Google News RSS로 투자자 관련 뉴스 검색 — 최신순 정렬."""
    slug = urllib.parse.quote(query)
    url = _GOOGLE_NEWS_RSS.format(query=slug)

    key = f"macro:investor_news:{query[:30]}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    raw = _parse_rss(url, max_items=max_items * 2)  # 여유있게 수집 후 정렬
    items = _dedup_and_sort(raw, max_items)
    if items:
        set_cached(key, items, ttl_hours=6)
    return items


# ── 수익률곡선 ──────────────────────────────────────────────────────────────

_YIELD_SYMBOLS = [
    ("^IRX", "3m"),
    ("^FVX", "5y"),
    ("^TNX", "10y"),
    ("^TYX", "30y"),
]


def fetch_yield_curve_data() -> dict:
    """미국 국채 수익률곡선 — 현재값 + 6개월 시계열 + 역전 여부."""
    key = "macro:yield_curve"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf

        current: dict[str, Optional[float]] = {}
        histories: dict[str, list] = {}

        def _fetch_yield(sym: str, label: str):
            try:
                t = yf.Ticker(sym)
                fi = t.fast_info
                val = _safe(fi.last_price) or _safe(fi.previous_close)
                hist = t.history(period="6mo", interval="1d")
                ts_list = []
                if not hist.empty:
                    for ts, row in hist.iterrows():
                        close = _safe(row["Close"])
                        if close is not None:
                            ts_list.append({
                                "date": ts.strftime("%Y-%m-%d"),
                                "value": round(close, 3),
                            })
                return label, val, ts_list
            except Exception as e:
                logger.warning("수익률곡선 %s 조회 실패: %s", sym, e)
                return label, None, []

        with ThreadPoolExecutor(max_workers=4) as pool:
            futs = [pool.submit(_fetch_yield, sym, label) for sym, label in _YIELD_SYMBOLS]
            for fut in as_completed(futs):
                label, val, ts_list = fut.result()
                current[label] = round(val, 3) if val is not None else None
                histories[label] = ts_list

        # 10Y-3M 스프레드
        y10 = current.get("10y")
        y3m = current.get("3m")
        spread = round(y10 - y3m, 3) if (y10 is not None and y3m is not None) else None

        # 시계열 스프레드 (날짜 정렬 — 3m과 10y 교차 매핑)
        h3m_map = {d["date"]: d["value"] for d in histories.get("3m", [])}
        h10y_map = {d["date"]: d["value"] for d in histories.get("10y", [])}
        all_dates = sorted(set(h3m_map.keys()) & set(h10y_map.keys()))
        history = []
        for dt in all_dates:
            v3m = h3m_map[dt]
            v10y = h10y_map[dt]
            history.append({
                "date": dt,
                "y3m": v3m,
                "y10y": v10y,
                "spread": round(v10y - v3m, 3),
            })

        result = {
            "current": current,
            "spread_10y_3m": spread,
            "history": history,
            "inverted": spread < 0 if spread is not None else False,
        }
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception as e:
        logger.warning("수익률곡선 데이터 조회 실패: %s", e)
        return {
            "current": {"3m": None, "5y": None, "10y": None, "30y": None},
            "spread_10y_3m": None,
            "history": [],
            "inverted": False,
        }


# ── 신용스프레드 ────────────────────────────────────────────────────────────

def fetch_credit_spread() -> dict:
    """HYG/LQD 기반 하이일드 신용스프레드 근사."""
    key = "macro:credit_spread"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        import yfinance as yf

        def _get_yield(sym: str) -> Optional[float]:
            try:
                t = yf.Ticker(sym)
                info = t.info
                y = _safe(info.get("yield"))
                if y is not None:
                    return round(y * 100, 3)  # decimal → %
                tady = _safe(info.get("trailingAnnualDividendYield"))
                if tady is not None:
                    return round(tady * 100, 3)
                return None
            except Exception:
                return None

        hyg_yield = _get_yield("HYG")
        lqd_yield = _get_yield("LQD")

        spread = round(hyg_yield - lqd_yield, 3) if (hyg_yield is not None and lqd_yield is not None) else None

        # 가격 기반 비율 시계열
        history = []
        direction = "stable"
        try:
            hyg_t = yf.Ticker("HYG")
            lqd_t = yf.Ticker("LQD")
            hyg_hist = hyg_t.history(period="6mo", interval="1d")
            lqd_hist = lqd_t.history(period="6mo", interval="1d")

            if not hyg_hist.empty and not lqd_hist.empty:
                # 날짜 교차
                hyg_map = {ts.strftime("%Y-%m-%d"): _safe(row["Close"]) for ts, row in hyg_hist.iterrows()}
                lqd_map = {ts.strftime("%Y-%m-%d"): _safe(row["Close"]) for ts, row in lqd_hist.iterrows()}
                common_dates = sorted(set(hyg_map.keys()) & set(lqd_map.keys()))

                for dt in common_dates:
                    hv = hyg_map[dt]
                    lv = lqd_map[dt]
                    if hv and lv:
                        ratio = round(hv / lv, 4)
                        history.append({"date": dt, "hyg": round(hv, 2), "lqd": round(lv, 2), "ratio": ratio})

                # 방향 판단: 최근 20일 MA vs 현재 비율
                if len(history) >= 20:
                    ratios = [h["ratio"] for h in history]
                    ma20 = sum(ratios[-20:]) / 20
                    current_ratio = ratios[-1]
                    diff = current_ratio - ma20
                    if diff < -0.002:
                        direction = "widening"   # HYG 상대 하락 = 스프레드 확대
                    elif diff > 0.002:
                        direction = "narrowing"  # HYG 상대 상승 = 스프레드 축소
                    else:
                        direction = "stable"
        except Exception as e:
            logger.warning("신용스프레드 시계열 조회 실패: %s", e)

        result = {
            "hyg_yield": hyg_yield,
            "lqd_yield": lqd_yield,
            "spread": spread,
            "spread_direction": direction,
            "history": history,
        }
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception as e:
        logger.warning("신용스프레드 조회 실패: %s", e)
        return {
            "hyg_yield": None,
            "lqd_yield": None,
            "spread": None,
            "spread_direction": "stable",
            "history": [],
        }


# ── 환율 ────────────────────────────────────────────────────────────────────

_CURRENCY_SYMBOLS = [
    ("USDKRW=X", "USD/KRW"),
    ("USDJPY=X", "USD/JPY"),
    ("EURUSD=X", "EUR/USD"),
    ("DX-Y.NYB", "달러인덱스"),
]


def fetch_currency_quotes() -> list[dict]:
    """주요 환율 현재가 + 1개월 스파크라인."""
    key = "macro:currencies"
    cached = get_cached(key)
    if cached is not None:
        return cached

    def _fetch_one(sym: str, name: str) -> Optional[dict]:
        try:
            import yfinance as yf
            t = yf.Ticker(sym)
            fi = t.fast_info

            price = _safe(fi.last_price) or _safe(fi.previous_close)
            if price is None:
                return None

            prev = _safe(fi.previous_close) or price
            change = round(price - prev, 4)
            change_pct = round((price - prev) / prev * 100, 2) if prev else 0

            hist = t.history(period="1mo", interval="1d")
            sparkline = []
            if not hist.empty:
                for ts, row in hist.iterrows():
                    close = _safe(row["Close"])
                    if close is not None:
                        sparkline.append({"date": ts.strftime("%Y-%m-%d"), "v": round(close, 4)})

            return {
                "symbol": sym,
                "name": name,
                "price": round(price, 4),
                "prev_close": round(prev, 4),
                "change": change,
                "change_pct": change_pct,
                "sparkline": sparkline,
            }
        except Exception as e:
            logger.warning("환율 조회 실패 (%s): %s", sym, e)
            return None

    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futs = {pool.submit(_fetch_one, sym, name): (sym, name) for sym, name in _CURRENCY_SYMBOLS}
        for fut in as_completed(futs):
            sym, name = futs[fut]
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    # 원래 순서 유지
    order_map = {sym: i for i, (sym, _) in enumerate(_CURRENCY_SYMBOLS)}
    results.sort(key=lambda x: order_map.get(x["symbol"], 99))

    if results:
        set_cached(key, results, ttl_hours=0.17)  # ~10분
    return results


# ── 원자재 ──────────────────────────────────────────────────────────────────

_COMMODITY_SYMBOLS = [
    ("CL=F", "WTI 원유"),
    ("GC=F", "금"),
    ("ZC=F", "옥수수"),
    ("ZW=F", "밀"),
    ("ZS=F", "대두"),
]


def fetch_commodity_quotes() -> list[dict]:
    """주요 원자재 현재가 + 1개월 스파크라인."""
    key = "macro:commodities"
    cached = get_cached(key)
    if cached is not None:
        return cached

    def _fetch_one(sym: str, name: str) -> Optional[dict]:
        try:
            import yfinance as yf
            t = yf.Ticker(sym)
            fi = t.fast_info

            price = _safe(fi.last_price) or _safe(fi.previous_close)
            if price is None:
                return None

            prev = _safe(fi.previous_close) or price
            change = round(price - prev, 2)
            change_pct = round((price - prev) / prev * 100, 2) if prev else 0

            hist = t.history(period="1mo", interval="1d")
            sparkline = []
            if not hist.empty:
                for ts, row in hist.iterrows():
                    close = _safe(row["Close"])
                    if close is not None:
                        sparkline.append({"date": ts.strftime("%Y-%m-%d"), "v": round(close, 2)})

            return {
                "symbol": sym,
                "name": name,
                "price": round(price, 2),
                "prev_close": round(prev, 2),
                "change": change,
                "change_pct": change_pct,
                "sparkline": sparkline,
            }
        except Exception as e:
            logger.warning("원자재 조회 실패 (%s): %s", sym, e)
            return None

    results = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = {pool.submit(_fetch_one, sym, name): (sym, name) for sym, name in _COMMODITY_SYMBOLS}
        for fut in as_completed(futs):
            sym, name = futs[fut]
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    order_map = {sym: i for i, (sym, _) in enumerate(_COMMODITY_SYMBOLS)}
    results.sort(key=lambda x: order_map.get(x["symbol"], 99))

    if results:
        set_cached(key, results, ttl_hours=0.17)  # ~10분
    return results


# ── 섹터 수익률 ─────────────────────────────────────────────────────────────

_SECTOR_ETFS = [
    ("XLK", "Technology", "기술"),
    ("XLF", "Financials", "금융"),
    ("XLE", "Energy", "에너지"),
    ("XLV", "Health Care", "헬스케어"),
    ("XLY", "Consumer Discretionary", "경기소비"),
    ("XLP", "Consumer Staples", "필수소비"),
    ("XLI", "Industrials", "산업재"),
    ("XLU", "Utilities", "유틸리티"),
    ("XLRE", "Real Estate", "부동산"),
    ("XLC", "Communication Services", "커뮤니케이션"),
    ("XLB", "Materials", "소재"),
]


def _calc_return(closes: list[float], n_days: int) -> Optional[float]:
    """n_days 기간 수익률(%). 데이터 부족 시 None."""
    if len(closes) < n_days + 1:
        return None
    try:
        return round((closes[-1] / closes[-n_days - 1] - 1) * 100, 2)
    except (ZeroDivisionError, IndexError):
        return None


def fetch_sector_returns() -> list[dict]:
    """11개 섹터 ETF 1M/3M/6M/1Y 수익률."""
    key = "macro:sector_returns"
    cached = get_cached(key)
    if cached is not None:
        return cached

    def _fetch_one(sym: str, name: str, name_ko: str) -> Optional[dict]:
        try:
            import yfinance as yf
            t = yf.Ticker(sym)
            hist = t.history(period="1y", interval="1d")
            if hist.empty:
                return None

            closes = [_safe(v) for v in hist["Close"].tolist()]
            closes = [c for c in closes if c is not None]
            if not closes:
                return None

            return {
                "symbol": sym,
                "name": name,
                "name_ko": name_ko,
                "return_1m": _calc_return(closes, 21),
                "return_3m": _calc_return(closes, 63),
                "return_6m": _calc_return(closes, 126),
                "return_1y": _calc_return(closes, 252),
                "price": round(closes[-1], 2),
            }
        except Exception as e:
            logger.warning("섹터 수익률 조회 실패 (%s): %s", sym, e)
            return None

    results = []
    with ThreadPoolExecutor(max_workers=11) as pool:
        futs = {pool.submit(_fetch_one, sym, name, name_ko): sym for sym, name, name_ko in _SECTOR_ETFS}
        for fut in as_completed(futs):
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    order_map = {sym: i for i, (sym, _, _) in enumerate(_SECTOR_ETFS)}
    results.sort(key=lambda x: order_map.get(x["symbol"], 99))

    if results:
        set_cached(key, results, ttl_hours=1)
    return results


# ── 경기사이클 입력 ─────────────────────────────────────────────────────────

def fetch_cycle_inputs() -> dict:
    """경기 사이클 판단에 필요한 6개 지표 수집."""
    key = "macro:cycle_inputs"
    cached = get_cached(key)
    if cached is not None:
        return cached

    result: dict = {
        "yield_spread": None,
        "yield_direction": "stable",
        "credit_direction": "stable",
        "vix_value": None,
        "vix_level": "normal",
        "sector_rotation": "mixed",
        "dollar_strength": "stable",
    }

    # 1) 수익률곡선
    try:
        yc = fetch_yield_curve_data()
        result["yield_spread"] = yc.get("spread_10y_3m")
        # 방향 판단: 최근 20일 스프레드 추세
        hist = yc.get("history", [])
        if len(hist) >= 20:
            recent = [h["spread"] for h in hist[-20:]]
            older = [h["spread"] for h in hist[-40:-20]] if len(hist) >= 40 else recent
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / len(older)
            diff = avg_recent - avg_older
            if diff > 0.1:
                result["yield_direction"] = "steepening"
            elif diff < -0.1:
                result["yield_direction"] = "flattening"
            else:
                result["yield_direction"] = "stable"
    except Exception as e:
        logger.warning("수익률곡선 입력 실패: %s", e)

    # 2) 신용스프레드
    try:
        cs = fetch_credit_spread()
        result["credit_direction"] = cs.get("spread_direction", "stable")
    except Exception as e:
        logger.warning("신용스프레드 입력 실패: %s", e)

    # 3) VIX
    try:
        vix = fetch_vix()
        if vix:
            result["vix_value"] = vix["value"]
            result["vix_level"] = vix["level"]
    except Exception as e:
        logger.warning("VIX 입력 실패: %s", e)

    # 4) 섹터 로테이션
    try:
        sectors = fetch_sector_returns()
        if sectors:
            sector_map = {s["symbol"]: s for s in sectors}
            cyclical_syms = ["XLY", "XLK", "XLF", "XLI"]
            defensive_syms = ["XLP", "XLU", "XLV"]

            cyclical_ret = []
            for sym in cyclical_syms:
                s = sector_map.get(sym)
                if s and s.get("return_3m") is not None:
                    cyclical_ret.append(s["return_3m"])

            defensive_ret = []
            for sym in defensive_syms:
                s = sector_map.get(sym)
                if s and s.get("return_3m") is not None:
                    defensive_ret.append(s["return_3m"])

            if cyclical_ret and defensive_ret:
                avg_cyc = sum(cyclical_ret) / len(cyclical_ret)
                avg_def = sum(defensive_ret) / len(defensive_ret)
                if avg_cyc - avg_def > 2:
                    result["sector_rotation"] = "cyclical"
                elif avg_def - avg_cyc > 2:
                    result["sector_rotation"] = "defensive"
                else:
                    result["sector_rotation"] = "mixed"
    except Exception as e:
        logger.warning("섹터 로테이션 입력 실패: %s", e)

    # 5) 달러 강도
    try:
        import yfinance as yf
        dx = yf.Ticker("DX-Y.NYB")
        hist = dx.history(period="2mo", interval="1d")
        if not hist.empty and len(hist) >= 20:
            closes = [_safe(v) for v in hist["Close"].tolist()]
            closes = [c for c in closes if c is not None]
            if len(closes) >= 20:
                current = closes[-1]
                ma20 = sum(closes[-20:]) / 20
                pct_diff = (current - ma20) / ma20 * 100
                if pct_diff > 1:
                    result["dollar_strength"] = "strengthening"
                elif pct_diff < -1:
                    result["dollar_strength"] = "weakening"
                else:
                    result["dollar_strength"] = "stable"
    except Exception as e:
        logger.warning("달러 강도 입력 실패: %s", e)

    set_cached(key, result, ttl_hours=1)
    return result

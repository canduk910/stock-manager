"""매크로 분석 데이터 수집.

yfinance 지수 데이터, RSS 뉴스 피드, 시장심리 지표.
"""
from __future__ import annotations

import logging
import math
import urllib.parse
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

_NAVER_RSS_URL = "https://news.google.com/rss/search?q=한국+경제+주식&hl=ko&gl=KR&ceid=KR:ko"
_NYT_RSS_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"
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

def _parse_rss(url: str, max_items: int = 15) -> list[dict]:
    """feedparser로 RSS 파싱."""
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
            })
        return items
    except Exception as e:
        logger.warning("RSS 파싱 실패 (%s): %s", url[:60], e)
        return []


def fetch_naver_news(max_items: int = 15) -> list[dict]:
    """한국 경제 뉴스 (Google News Korea RSS 경유)."""
    key = "macro:news:naver"
    cached = get_cached(key)
    if cached is not None:
        return cached

    items = _parse_rss(_NAVER_RSS_URL, max_items)
    if items:
        set_cached(key, items, ttl_hours=0.5)
    return items


def fetch_nyt_news(max_items: int = 10) -> list[dict]:
    """NYT Business 뉴스 RSS."""
    key = "macro:news:nyt_raw"
    cached = get_cached(key)
    if cached is not None:
        return cached

    items = _parse_rss(_NYT_RSS_URL, max_items)
    if items:
        set_cached(key, items, ttl_hours=0.5)
    return items


def fetch_investor_news(query: str, max_items: int = 5) -> list[dict]:
    """Google News RSS로 투자자 관련 뉴스 검색."""
    slug = urllib.parse.quote(query)
    url = _GOOGLE_NEWS_RSS.format(query=slug)

    key = f"macro:investor_news:{query[:30]}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    items = _parse_rss(url, max_items)
    if items:
        set_cached(key, items, ttl_hours=6)
    return items

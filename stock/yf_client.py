"""yfinance 기반 해외주식 데이터 수집.

stock/market.py (국내 pykrx) 와 stock/dart_fin.py (국내 DART) 의 해외주식 버전.
시세는 15분 지연이며, 재무는 최대 4년을 제공한다.
"""

from __future__ import annotations

import math
from typing import Optional

from stock.cache import get_cached, set_cached


def _ticker(code: str):
    """yfinance Ticker 객체 반환."""
    import yfinance as yf
    return yf.Ticker(code.upper())


def _safe(v) -> Optional[float]:
    """NaN/Inf를 None으로 변환. JSON 직렬화 안전."""
    if v is None:
        return None
    try:
        fv = float(v)
        return None if (math.isnan(fv) or math.isinf(fv)) else fv
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    """NaN/Inf 제외 후 int 변환."""
    fv = _safe(v)
    return int(fv) if fv is not None else None


# ── 종목 검증 ─────────────────────────────────────────────────────────────────

def validate_ticker(code: str) -> Optional[dict]:
    """ticker가 유효한지 확인하고 기본 정보를 반환. 없으면 None."""
    key = f"yf:validate:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        info = _ticker(code).info
        # yfinance는 존재하지 않는 티커에도 빈 dict 또는 최소 정보만 반환함
        if not info or info.get("quoteType") is None:
            set_cached(key, {}, ttl_hours=1)
            return None
        result = {
            "name": info.get("longName") or info.get("shortName") or code.upper(),
            "exchange": info.get("exchange", ""),
            "quote_type": info.get("quoteType", ""),
        }
        set_cached(key, result, ttl_hours=24)
        return result
    except Exception:
        set_cached(key, {}, ttl_hours=1)
        return None


# ── 현재가 ────────────────────────────────────────────────────────────────────

def fetch_price_yf(code: str) -> Optional[dict]:
    """현재가/등락/시가총액 (USD 기준). 15분 지연."""
    key = f"yf:price:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        t = _ticker(code)
        fi = t.fast_info
        close = _safe(fi.last_price)
        if close is None:
            set_cached(key, {}, ttl_hours=1)
            return None

        prev_close = _safe(fi.previous_close) or close
        change = _safe(round(close - prev_close, 4)) if prev_close else None
        change_pct = _safe(round((close - prev_close) / prev_close * 100, 2)) if prev_close else None
        mktcap = _safe(fi.market_cap)

        result = {
            "code": code.upper(),
            "close": _safe(round(close, 4)),
            "change": change,
            "change_pct": change_pct,
            "mktcap": mktcap,
            "currency": fi.currency or "USD",
        }
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception:
        set_cached(key, {}, ttl_hours=1)
        return None


# ── 상세 정보 ─────────────────────────────────────────────────────────────────

def fetch_detail_yf(code: str) -> Optional[dict]:
    """시세 + 52주 고저 + P/E + 업종/거래소."""
    key = f"yf:detail:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    try:
        t = _ticker(code)
        info = t.info
        if not info or info.get("quoteType") is None:
            set_cached(key, {}, ttl_hours=1)
            return None

        fi = t.fast_info
        close = _safe(fi.last_price) or _safe(info.get("currentPrice")) or _safe(info.get("regularMarketPrice"))
        if close is None:
            set_cached(key, {}, ttl_hours=1)
            return None

        prev_close = _safe(fi.previous_close) or _safe(info.get("previousClose")) or close
        change = _safe(round(close - prev_close, 4)) if prev_close else None
        change_pct = _safe(round((close - prev_close) / prev_close * 100, 2)) if prev_close else None
        mktcap = _safe(fi.market_cap) or _safe(info.get("marketCap"))

        result = {
            "code": code.upper(),
            "name": info.get("longName") or info.get("shortName") or code.upper(),
            "close": _safe(round(close, 4)),
            "change": change,
            "change_pct": change_pct,
            "mktcap": mktcap,
            "currency": fi.currency or info.get("currency", "USD"),
            "market_type": info.get("exchange", ""),
            "sector": info.get("sector", ""),
            "high_52": _safe(info.get("fiftyTwoWeekHigh")),
            "low_52": _safe(info.get("fiftyTwoWeekLow")),
            "per": _safe(info.get("trailingPE") or info.get("forwardPE")),
            "pbr": _safe(info.get("priceToBook")),
        }
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception:
        set_cached(key, {}, ttl_hours=1)
        return None


# ── 수익률 ────────────────────────────────────────────────────────────────────

def fetch_period_returns_yf(code: str) -> dict:
    """당일/3M/6M/1Y 수익률."""
    key = f"yf:returns:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        hist = _ticker(code).history(period="1y")
        if hist.empty:
            result: dict = {}
            set_cached(key, result, ttl_hours=1)
            return result

        closes = hist["Close"]
        last = float(closes.iloc[-1])
        prev = float(closes.iloc[-2]) if len(closes) >= 2 else last

        def _ret(n_days: int) -> Optional[float]:
            if len(closes) < n_days:
                return None
            base = float(closes.iloc[-n_days])
            if base == 0:
                return None
            return _safe(round((last - base) / base * 100, 2))

        result = {
            "change_pct": _safe(round((last - prev) / prev * 100, 2)) if prev else None,
            "return_3m": _ret(63),   # ~3개월(영업일)
            "return_6m": _ret(126),
            "return_1y": _ret(252),
        }
        set_cached(key, result, ttl_hours=1)
        return result
    except Exception:
        return {}


# ── 재무 ──────────────────────────────────────────────────────────────────────

def fetch_financials_yf(code: str) -> Optional[dict]:
    """최근 연도 재무 (USD). 대시보드용 단일 row."""
    key = f"yf:fin_latest:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached or None

    rows = fetch_financials_multi_year_yf(code, years=1)
    if not rows:
        set_cached(key, {}, ttl_hours=24)
        return None
    result = rows[-1]
    set_cached(key, result, ttl_hours=24)
    return result


def fetch_financials_multi_year_yf(code: str, years: int = 4) -> list[dict]:
    """다년도 재무 (yfinance 최대 4년, USD).

    반환: [{year, revenue, operating_income, net_income}, ...]  과거 → 최신 순.
    국내 dart_fin.py 와 동일한 인터페이스. dart_url 없음.
    """
    key = f"yf:fin_multi:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        t = _ticker(code)
        fin = t.financials  # 연간 손익계산서 (columns = 날짜, index = 항목)
        if fin is None or fin.empty:
            set_cached(key, [], ttl_hours=24)
            return []

        rows = []
        for col in sorted(fin.columns, reverse=False):  # 오래된 연도 먼저
            year = col.year

            def _get(*names):
                for n in names:
                    if n in fin.index:
                        v = fin.loc[n, col]
                        return _safe_int(v)
                return None

            revenue = _get("Total Revenue", "Revenue")
            op_inc = _get("Operating Income", "EBIT")
            net_inc = _get("Net Income", "Net Income Common Stockholders")
            rows.append({
                "year": year,
                "revenue": revenue,
                "operating_income": op_inc,
                "net_income": net_inc,
                "dart_url": "",
            })

        # 최대 years개만
        rows = rows[-years:] if len(rows) > years else rows
        set_cached(key, rows, ttl_hours=24)
        return rows
    except Exception:
        set_cached(key, [], ttl_hours=24)
        return []

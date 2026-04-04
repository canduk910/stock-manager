"""yfinance 기반 해외주식 데이터 수집.

stock/market.py (국내 pykrx) 와 stock/dart_fin.py (국내 DART) 의 해외주식 버전.
시세는 15분 지연이며, 재무는 최대 4년을 제공한다.
"""

from __future__ import annotations

import math
from typing import Optional

from stock.cache import get_cached, set_cached
from stock.market import _is_us_trading_hours


def _ticker(code: str):
    """yfinance Ticker 객체 반환 (LRU 캐시로 중복 생성 방지)."""
    import yfinance as yf
    return yf.Ticker(code.upper())


# lru_cache를 _ticker 자체에 적용하면 Ticker 내부 상태가 stale될 수 있으므로
# 별도 캐시 dict + TTL 없이 maxsize 제한만 적용
from functools import lru_cache as _lru_cache
_ticker = _lru_cache(maxsize=256)(_ticker)


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
        # 비개장일에 last_price가 None인 경우 previous_close로 fallback
        close = _safe(fi.last_price) or _safe(fi.previous_close)
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
        ttl = 2 / 60 if _is_us_trading_hours() else 0.5  # 장중 2분, 장외 30분
        set_cached(key, result, ttl_hours=ttl)
        # 영속 캐시 write-through
        try:
            from .stock_info_store import upsert_price
            upsert_price(code, "US", result)
        except Exception:
            pass
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

        roe_raw = info.get("returnOnEquity")
        roe = _safe(round(roe_raw * 100, 2)) if roe_raw is not None else None

        # dividendYield: 이미 % 형태 (0.4, 1.3) → 우선 사용
        # trailingAnnualDividendYield: 소수점 형태 → ×100 변환 (ADR 오계산 가능)
        # dividendRate(연간 주당배당금) ÷ 현재가 → 마지막 fallback
        div_yield_pct  = info.get("dividendYield")
        trailing_yield = info.get("trailingAnnualDividendYield")
        div_rate       = info.get("dividendRate")
        if div_yield_pct is not None:
            dividend_yield = _safe(round(float(div_yield_pct), 2))
        elif trailing_yield is not None:
            dividend_yield = _safe(round(trailing_yield * 100, 2))
        elif div_rate and close and close > 0:
            computed = float(div_rate) / float(close) * 100
            dividend_yield = _safe(round(computed, 2)) if 0 < computed < 50 else None
        else:
            dividend_yield = None

        div_per_share_raw = info.get("dividendRate")  # 연간 주당배당금 (현지통화)
        dividend_per_share = _safe(round(float(div_per_share_raw), 4)) if div_per_share_raw else None

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
            "roe": roe,
            "dividend_yield": dividend_yield,
            "dividend_per_share": dividend_per_share,
        }
        ttl = 0.5 if _is_us_trading_hours() else 6  # 장중 30분, 장외 6시간
        set_cached(key, result, ttl_hours=ttl)
        # 영속 캐시 write-through
        try:
            from .stock_info_store import upsert_metrics
            upsert_metrics(code, "US", result)
        except Exception:
            pass
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
        ttl = 0.25 if _is_us_trading_hours() else 6  # 장중 15분, 장외 6시간
        set_cached(key, result, ttl_hours=ttl)
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
    # 영속 캐시 write-through
    try:
        from .stock_info_store import upsert_financials
        upsert_financials(code, "US", {**result, "bsns_year": result.get("year")})
    except Exception:
        pass
    return result


def fetch_financials_multi_year_yf(code: str, years: int = 4) -> list[dict]:
    """다년도 재무 (yfinance 최대 4년, USD).

    반환: [{year, revenue, operating_income, net_income}, ...]  과거 → 최신 순.
    국내 dart_fin.py 와 동일한 인터페이스. dart_url 없음.
    """
    key = f"yf:fin_multi:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached[-years:] if len(cached) > years else cached

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

        # 전체 rows를 캐시에 저장 (슬라이싱 전)
        set_cached(key, rows, ttl_hours=24)
        return rows[-years:] if len(rows) > years else rows
    except Exception:
        set_cached(key, [], ttl_hours=24)
        return []


# ── 대차대조표 ────────────────────────────────────────────────────────────────

_YF_BS_MAP = {
    "total_assets":        "Total Assets",
    "current_assets":      "Current Assets",
    "non_current_assets":  "Net PPE",          # 대체: non-current 직접 없음
    "cash_and_equiv":      "Cash And Cash Equivalents",
    "receivables":         "Accounts Receivable",
    "inventories":         "Inventory",
    "ppe":                 "Net PPE",
    "total_liabilities":   "Total Liabilities Net Minority Interest",
    "current_liabilities": "Current Liabilities",
    "long_term_debt":      "Long Term Debt",
    "total_equity":        "Stockholders Equity",
    "retained_earnings":   "Retained Earnings",
}


def fetch_balance_sheet_yf(code: str, years: int = 5) -> list[dict]:
    """yfinance 연간 대차대조표. [{year, total_assets, ...}] 과거→최신 순."""
    key = f"yf:balance_sheet:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached[-years:] if len(cached) > years else cached

    try:
        t = _ticker(code)
        bs = t.balance_sheet
        if bs is None or bs.empty:
            set_cached(key, [], ttl_hours=24)
            return []

        rows = []
        for col in sorted(bs.columns, reverse=False):
            year = col.year
            row: dict = {"year": year}
            for field, yf_name in _YF_BS_MAP.items():
                val = None
                if yf_name in bs.index:
                    val = _safe_int(bs.loc[yf_name, col])
                row[field] = val

            # 비유동자산 = 자산총계 - 유동자산
            ta = row.get("total_assets") or 0
            ca = row.get("current_assets") or 0
            row["non_current_assets"] = (ta - ca) if (ta and ca) else None

            # 부채비율, 유동비율
            equity = row.get("total_equity") or 0
            liab = row.get("total_liabilities") or 0
            cur_a = row.get("current_assets") or 0
            cur_l = row.get("current_liabilities") or 1
            row["debt_ratio"] = round(liab / equity * 100, 1) if equity else None
            row["current_ratio"] = round(cur_a / cur_l * 100, 1) if cur_l else None
            rows.append(row)

        set_cached(key, rows, ttl_hours=24)
        return rows[-years:] if len(rows) > years else rows
    except Exception:
        set_cached(key, [], ttl_hours=24)
        return []


# ── 현금흐름표 ────────────────────────────────────────────────────────────────

_YF_CF_MAP = {
    "operating_cf":  "Operating Cash Flow",
    "investing_cf":  "Investing Cash Flow",
    "financing_cf":  "Financing Cash Flow",
    "capex":         "Capital Expenditure",
    "depreciation":  "Depreciation And Amortization",
    "free_cf":       "Free Cash Flow",
}


def fetch_cashflow_yf(code: str, years: int = 5) -> list[dict]:
    """yfinance 연간 현금흐름표. [{year, operating_cf, ...}] 과거→최신 순."""
    key = f"yf:cashflow:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached[-years:] if len(cached) > years else cached

    try:
        t = _ticker(code)
        cf = t.cashflow
        if cf is None or cf.empty:
            set_cached(key, [], ttl_hours=24)
            return []

        rows = []
        for col in sorted(cf.columns, reverse=False):
            year = col.year
            row: dict = {"year": year}
            for field, yf_name in _YF_CF_MAP.items():
                val = None
                if yf_name in cf.index:
                    val = _safe_int(cf.loc[yf_name, col])
                row[field] = val

            # free_cf 없으면 영업CF - |CAPEX| 계산
            if row.get("free_cf") is None:
                op_cf = row.get("operating_cf") or 0
                capex = row.get("capex") or 0
                row["free_cf"] = op_cf - abs(capex)

            rows.append(row)

        set_cached(key, rows, ttl_hours=24)
        return rows[-years:] if len(rows) > years else rows
    except Exception:
        set_cached(key, [], ttl_hours=24)
        return []


# ── 손익계산서 세부 ────────────────────────────────────────────────────────────

def fetch_income_detail_yf(code: str, years: int = 5) -> list[dict]:
    """yfinance 손익계산서 세부. [{year, revenue, cogs, gross_profit, ...}]"""
    key = f"yf:income_detail:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached[-years:] if len(cached) > years else cached

    try:
        t = _ticker(code)
        fin = t.financials
        if fin is None or fin.empty:
            set_cached(key, [], ttl_hours=24)
            return []

        rows = []
        for col in sorted(fin.columns, reverse=False):
            year = col.year

            def _g(*names):
                for n in names:
                    if n in fin.index:
                        return _safe_int(fin.loc[n, col])
                return None

            revenue = _g("Total Revenue", "Revenue")
            cogs = _g("Cost Of Revenue")
            gross = _g("Gross Profit")
            sga = _g("Selling General And Administrative")
            op_inc = _g("Operating Income", "EBIT")
            interest_exp = _g("Interest Expense")
            pretax = _g("Pretax Income")
            tax = _g("Tax Provision")
            net_inc = _g("Net Income", "Net Income Common Stockholders")
            eps = _safe(fin.loc["Basic EPS", col]) if "Basic EPS" in fin.index else None

            rev = revenue or 0
            oi = op_inc or 0
            ni = net_inc or 0
            rows.append({
                "year": year,
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross,
                "sga": sga,
                "operating_income": op_inc,
                "interest_income": None,
                "interest_expense": interest_exp,
                "pretax_income": pretax,
                "tax_expense": tax,
                "net_income": net_inc,
                "eps": eps,
                "oi_margin": round(oi / rev * 100, 1) if rev else None,
                "net_margin": round(ni / rev * 100, 1) if rev else None,
                "dart_url": "",
            })

        set_cached(key, rows, ttl_hours=24)
        return rows[-years:] if len(rows) > years else rows
    except Exception:
        set_cached(key, [], ttl_hours=24)
        return []


# ── 계량지표 ──────────────────────────────────────────────────────────────────

def fetch_metrics_yf(code: str) -> dict:
    """계량지표: {per, pbr, psr, ev_ebitda, ev, market_cap, roe, roa, debt_to_equity, current_ratio}"""
    key = f"yf:metrics:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        t = _ticker(code)
        info = t.info or {}

        roe_raw = info.get("returnOnEquity")
        roa_raw = info.get("returnOnAssets")
        roe = _safe(round(roe_raw * 100, 2)) if roe_raw is not None else None
        roa = _safe(round(roa_raw * 100, 2)) if roa_raw is not None else None

        eps = _safe(info.get("trailingEps"))
        bps = _safe(info.get("bookValue"))
        graham_number = None
        if eps and eps > 0 and bps and bps > 0:
            import math
            graham_number = round(math.sqrt(22.5 * eps * bps), 2)

        result = {
            "per":             _safe(info.get("trailingPE") or info.get("forwardPE")),
            "pbr":             _safe(info.get("priceToBook")),
            "psr":             _safe(info.get("priceToSalesTrailing12Months")),
            "ev_ebitda":       _safe(info.get("enterpriseToEbitda")),
            "ev":              _safe(info.get("enterpriseValue")),
            "market_cap":      _safe(info.get("marketCap")),
            "shares":          _safe(info.get("sharesOutstanding")),
            "roe":             roe,
            "roa":             roa,
            "debt_to_equity":  _safe(info.get("debtToEquity")),
            "current_ratio":   _safe(info.get("currentRatio")),
            "eps":             eps,
            "graham_number":   graham_number,
        }
        ttl = 0.5 if _is_us_trading_hours() else 6  # 장중 30분, 장외 6시간
        set_cached(key, result, ttl_hours=ttl)
        return result
    except Exception:
        empty: dict = {}
        set_cached(key, empty, ttl_hours=1)
        return empty


# ── 밸류에이션 히스토리 ───────────────────────────────────────────────────────

def fetch_valuation_history_yf(code: str, years: int = 5) -> list[dict]:
    """분기 재무 + 일별 주가를 조합해 월별 PER/PBR 히스토리 반환.

    - PER: 월말 종가 ÷ TTM EPS (해당 날짜 이전 최근 4분기 EPS 합산)
    - PBR: 월말 종가 ÷ BPS (해당 날짜 이전 최근 분기 equity ÷ shares)

    반환: [{date: "YYYY-MM", per: float|None, pbr: float|None}, ...]  오래된순
    """
    key = f"yf:valuation_hist:{code.upper()}:{years}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    try:
        import pandas as pd

        t = _ticker(code)

        # 1. 분기 손익계산서 → EPS 시계열
        qfin = t.quarterly_financials
        eps_series = None
        if qfin is not None and not qfin.empty:
            for name in ("Basic EPS", "Diluted EPS"):
                if name in qfin.index:
                    eps_series = qfin.loc[name].sort_index()  # 오래된→최신
                    break

        # 2. 분기 대차대조표 → equity 시계열
        qbs = t.quarterly_balance_sheet
        eq_series = None
        if qbs is not None and not qbs.empty:
            for name in ("Stockholders Equity", "Common Stock Equity"):
                if name in qbs.index:
                    eq_series = qbs.loc[name].sort_index()
                    break

        # 3. 발행주식수 시계열 (분기별) + 현재값 fallback
        shares_series = None
        if qbs is not None and not qbs.empty:
            for name in ("Ordinary Shares Number", "Share Issued"):
                if name in qbs.index:
                    shares_series = qbs.loc[name].dropna().sort_index()
                    break

        shares_current = None
        try:
            shares_current = _safe(t.fast_info.shares)
        except Exception:
            pass
        if not shares_current:
            shares_current = _safe((t.info or {}).get("sharesOutstanding"))

        # 4. 일별 주가 → 월별 마지막 종가
        hist = t.history(period=f"{years}y")
        if hist.empty:
            set_cached(key, [], ttl_hours=24)
            return []

        monthly = hist["Close"].resample("ME").last().dropna()

        result = []
        for ts, price in monthly.items():
            price_val = _safe(float(price))
            if price_val is None or price_val <= 0:
                continue

            date_label = ts.strftime("%Y-%m")
            # tz-aware→tz-naive 변환 (eps/eq_series는 tz-naive)
            ts_naive = ts.tz_localize(None) if ts.tzinfo else ts

            # PER: TTM EPS (해당 날짜 이전 최근 4분기 합산)
            per = None
            if eps_series is not None:
                past = eps_series[eps_series.index <= ts_naive]
                if len(past) >= 4:
                    ttm = _safe(float(past.iloc[-4:].sum()))
                    if ttm and ttm > 0:
                        per = _safe(round(price_val / ttm, 1))
                elif len(past) >= 1:
                    # 4분기 미만이면 최근값 × 4로 연환산
                    latest = _safe(float(past.iloc[-1]))
                    if latest and latest > 0:
                        per = _safe(round(price_val / (latest * 4), 1))

            # 해당 월 기준 발행주식수 (분기별 시계열에서 최근값)
            shares = shares_current  # fallback
            if shares_series is not None and len(shares_series) > 0:
                past_shares = shares_series[shares_series.index <= ts_naive]
                if len(past_shares) >= 1:
                    shares = int(past_shares.iloc[-1])

            # PBR: BPS = equity ÷ shares
            pbr = None
            if eq_series is not None and shares:
                past_eq = eq_series[eq_series.index <= ts_naive]
                if len(past_eq) >= 1:
                    eq = _safe(float(past_eq.iloc[-1]))
                    if eq and eq > 0:
                        bps = eq / shares
                        if bps > 0:
                            pbr = _safe(round(price_val / bps, 2))

            # PER 이상치 제거 (0 이하 또는 500 초과)
            if per is not None and (per <= 0 or per > 500):
                per = None

            mktcap = None
            if price_val and shares:
                mktcap = round(price_val * shares)
            result.append({"date": date_label, "per": per, "pbr": pbr,
                           "mktcap": mktcap, "shares": int(shares) if shares else None})

        set_cached(key, result, ttl_hours=24)
        return result

    except Exception:
        set_cached(key, [], ttl_hours=24)
        return []


# ── 사업별 매출비중 ────────────────────────────────────────────────────────────

def fetch_segments_yf(code: str) -> dict:
    """사업별 매출비중 + 사업 설명 + 키워드 (best effort).

    yfinance .info 에서 추출 가능한 세그먼트/사업설명/섹터·산업 반환.
    반환: {"segments": [...], "description": str, "keywords": [str]}
    """
    key = f"yf:segments_v2:{code.upper()}"
    cached = get_cached(key)
    if cached is not None:
        return cached

    empty: dict = {"segments": [], "description": "", "keywords": []}
    try:
        t = _ticker(code)
        info = t.info or {}

        # 세그먼트 (yfinance에 공식 세그먼트 API 없음 → sector 수준)
        sector = info.get("sector", "")
        segments: list[dict] = []
        if sector:
            segments.append({"segment": sector, "revenue_pct": 100.0, "note": "섹터"})

        # 사업 설명
        description = info.get("longBusinessSummary", "")
        if description and len(description) > 300:
            description = description[:297] + "..."

        # 키워드 (sector + industry)
        keywords: list[str] = []
        if sector:
            keywords.append(sector)
        industry = info.get("industry", "")
        if industry:
            keywords.append(industry)

        result = {"segments": segments, "description": description, "keywords": keywords}
        set_cached(key, result, ttl_hours=24)
        return result
    except Exception:
        set_cached(key, empty, ttl_hours=6)
        return empty


# ── 포워드 가이던스 / 애널리스트 컨센서스 ────────────────────────────────────

def _fmt_fiscal_year_end(ts) -> Optional[str]:
    """Unix timestamp → 'YYYY-MM' 문자열."""
    if not ts:
        return None
    try:
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m")
    except Exception:
        return None


def fetch_forward_estimates_yf(code: str, is_kr: bool = False) -> dict:
    """애널리스트 컨센서스 포워드 추정치 조회.

    US: yfinance info에서 비교적 풍부하게 제공.
    KR: .KS/.KQ suffix로 시도, 없으면 None 반환.

    반환:
    {
        "eps_current_year":        float | None,  # 현재 회계연도 EPS 추정
        "eps_forward":             float | None,  # 다음 회계연도 EPS 추정
        "forward_pe":              float | None,  # 포워드 PER
        "revenue_current":         float | None,  # 현재 회계연도 매출 추정
        "target_mean_price":       float | None,  # 애널리스트 목표가 평균
        "target_high_price":       float | None,  # 목표가 상단
        "target_low_price":        float | None,  # 목표가 하단
        "num_analysts":            int   | None,  # 평가 애널리스트 수
        "recommendation":          str   | None,  # "buy"/"hold"/"sell" 등
        "current_fiscal_year_end": str   | None,  # "2025-12" 형식
    }
    """
    cache_key = f"yf:forward:{code.upper()}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    ticker_str: str
    if is_kr:
        from stock.market import _kr_yf_ticker_str
        ticker_str = _kr_yf_ticker_str(code)
    else:
        ticker_str = code.upper()

    empty: dict = {}

    try:
        import yfinance as yf
        t = yf.Ticker(ticker_str)
        info = t.info or {}

        # 매출 추정치: 3단계 fallback (revenue_estimate → analysis → totalRevenue×growth)
        rev_estimate: Optional[float] = None
        rev_forward: Optional[float] = None
        try:
            import pandas as pd

            # 1단계: t.revenue_estimate (yfinance 0.2.30+, 더 안정적)
            try:
                rev_df = getattr(t, 'revenue_estimate', None)
                if rev_df is not None and not rev_df.empty:
                    # avg 컬럼 우선, 없으면 첫 컬럼
                    col = 'avg' if 'avg' in rev_df.columns else rev_df.columns[0]
                    if '0y' in rev_df.index:
                        val = rev_df.loc['0y', col]
                        if not pd.isna(val):
                            rev_estimate = float(val)
                    elif len(rev_df.index) > 0:
                        val = rev_df.iloc[0][col]
                        if not pd.isna(val):
                            rev_estimate = float(val)
                    if '+1y' in rev_df.index:
                        val2 = rev_df.loc['+1y', col]
                        if not pd.isna(val2):
                            rev_forward = float(val2)
                    elif len(rev_df.index) > 1:
                        val2 = rev_df.iloc[1][col]
                        if not pd.isna(val2):
                            rev_forward = float(val2)
            except Exception:
                pass

            # 2단계: t.analysis (레거시 방식)
            if rev_estimate is None:
                try:
                    analysis = t.analysis
                    if analysis is not None and not analysis.empty and "Revenue Estimate" in analysis.columns:
                        if "0y" in analysis.index:
                            val = analysis.loc["0y", "Revenue Estimate"]
                            if not pd.isna(val):
                                rev_estimate = float(val)
                        elif len(analysis.index) > 0:
                            val = analysis.iloc[0]["Revenue Estimate"]
                            if not pd.isna(val):
                                rev_estimate = float(val)
                        if rev_forward is None and "+1y" in analysis.index:
                            val2 = analysis.loc["+1y", "Revenue Estimate"]
                            if not pd.isna(val2):
                                rev_forward = float(val2)
                except Exception:
                    pass

            # 3단계: totalRevenue × (1 + revenueGrowth) fallback
            if rev_estimate is None:
                total_rev = _safe(info.get("totalRevenue"))
                rev_growth = _safe(info.get("revenueGrowth"))
                if total_rev and total_rev > 0:
                    if rev_growth is not None:
                        rev_estimate = total_rev * (1 + rev_growth)
                    else:
                        rev_estimate = total_rev  # 성장률 미지 시 현재 매출 그대로
        except Exception:
            pass

        # 순이익 추정: EPS × 발행주식수
        eps_cy = _safe(info.get("epsCurrentYear"))
        eps_fw = _safe(info.get("epsForward"))
        shares = _safe_int(info.get("sharesOutstanding"))
        net_income_estimate: Optional[float] = None
        net_income_forward: Optional[float] = None
        if shares and eps_cy is not None:
            net_income_estimate = eps_cy * shares
        if shares and eps_fw is not None:
            net_income_forward = eps_fw * shares

        result = {
            "eps_current_year":        eps_cy,
            "eps_forward":             eps_fw,
            "forward_pe":              _safe(info.get("forwardPE")),
            "revenue_current":         rev_estimate,
            "revenue_forward":         rev_forward,
            "net_income_estimate":     net_income_estimate,
            "net_income_forward":      net_income_forward,
            "shares_outstanding":      shares,
            "target_mean_price":       _safe(info.get("targetMeanPrice")),
            "target_high_price":       _safe(info.get("targetHighPrice")),
            "target_low_price":        _safe(info.get("targetLowPrice")),
            "num_analysts":            _safe_int(info.get("numberOfAnalystOpinions")),
            "recommendation":          info.get("recommendationKey") or None,
            "current_fiscal_year_end": _fmt_fiscal_year_end(info.get("nextFiscalYearEnd")),
        }

        # 모든 값이 None이면 빈 dict 캐싱 (데이터 없음)
        has_data = any(v is not None for v in result.values())
        payload = result if has_data else empty
        set_cached(cache_key, payload, ttl_hours=6)
        return payload

    except Exception:
        set_cached(cache_key, empty, ttl_hours=1)
        return empty

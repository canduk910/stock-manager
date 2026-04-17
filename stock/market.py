"""국내 주식 시세 · 시가총액 · 52주 고저 조회 — yfinance 기반.

pykrx KRX 스크래핑이 2026-02-27 이후 KRX 서버 변경(로그인 필수화)으로
동작 불가해짐. yfinance (.KS KOSPI / .KQ KOSDAQ suffix)로 대체.

제약사항:
  - PER / PBR: yfinance 국내 주식 미지원 → None 반환
  - 밸류에이션 히스토리: 미지원 → 빈 배열 반환
  - 섹터명: 영문 반환
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from .cache import delete_prefix, get_cached, set_cached


# ── 장중/장외 판별 ──────────────────────────────────────────────────────────────

_KST = timezone(timedelta(hours=9))


def _is_kr_trading_hours() -> bool:
    """KST 기준 월-금 09:00~15:30 여부."""
    now = datetime.now(_KST)
    if now.weekday() >= 5:  # 토, 일
        return False
    t = now.time()
    from datetime import time as dt_time
    return dt_time(9, 0) <= t <= dt_time(15, 30)


def _is_us_trading_hours() -> bool:
    """미국 동부 기준 월-금 09:30~16:00 여부 (DST 자동 반영)."""
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        now = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        # fallback: UTC-5 고정
        now = datetime.now(timezone(timedelta(hours=-5)))
    if now.weekday() >= 5:
        return False
    t = now.time()
    from datetime import time as dt_time
    return dt_time(9, 30) <= t <= dt_time(16, 0)


# ── yfinance ticker 헬퍼 ──────────────────────────────────────────────────────

def _kr_yf_ticker_str(code: str) -> Optional[str]:
    """국내 종목코드 → yfinance ticker 문자열 ('XXXXXX.KS' 또는 'XXXXXX.KQ').

    양쪽 suffix 모두 조회한 후 market_cap + shares가 있는 것을 우선 선택.
    (일부 코드가 .KS/.KQ 양쪽에 존재할 수 있으므로 데이터 완전성으로 판별)
    결과 7일 캐시.
    """
    cache_key = f"market:kr_yf_ticker:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached or None  # 빈 문자열 '' → None

    from .yf_client import _ticker

    best: Optional[str] = None
    # 최소 score ≥ 1 요구 (mktcap 또는 shares 중 하나 이상 필수).
    # score=0(price만 있고 mktcap/shares 없음)이면 잘못된 suffix일 가능성 높음.
    # 예: 267260(HD현대일렉트릭)은 .KS(KOSPI)가 정상이나, .KQ 조회 시
    #     price만 반환되고 mktcap=None → 잘못된 데이터가 7일 캐시되는 버그 방지.
    best_score = 0

    for suffix in [".KS", ".KQ"]:
        try:
            fi = _ticker(f"{code}{suffix}").fast_info
            price = fi.last_price
            if not price or price <= 0:
                continue
            score = 0
            if fi.market_cap and fi.market_cap > 0:
                score += 1
            if fi.shares and fi.shares > 0:
                score += 1
            if score > best_score:
                best = f"{code}{suffix}"
                best_score = score
            # score=2이면 완전한 데이터 → 추가 suffix 시도 불필요
            if best_score >= 2:
                break
        except Exception:
            pass

    if best:
        set_cached(cache_key, best, ttl_hours=24 * 7)
    else:
        set_cached(cache_key, "", ttl_hours=1)
    return best


def _market_type(ticker_str: str) -> str:
    """ticker suffix → KOSPI / KOSDAQ 구분."""
    return "KOSPI" if ticker_str.endswith(".KS") else "KOSDAQ"


# ── 공개 API ──────────────────────────────────────────────────────────────────

def fetch_price(code: str, refresh: bool = False) -> Optional[dict]:
    """현재가, 전일대비(%), 시가총액, 상장주식수 조회.

    반환: dict 또는 None (종목 없음)
    """
    cache_key = f"market:price:{code}"
    if refresh:
        delete_prefix(f"market:price:{code}")
        delete_prefix(f"market:kr_yf_ticker:{code}")
    else:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None

    try:
        fi = _ticker(ticker_str).fast_info

        close = fi.last_price
        prev_close = fi.previous_close

        if not close or close <= 0:
            return None

        change = round(close - prev_close) if prev_close else 0
        change_pct = (
            round((close - prev_close) / prev_close * 100, 2) if prev_close else 0.0
        )

        mktcap = fi.market_cap
        shares = fi.shares

        result = {
            "code": code,
            "close": int(close),
            "change": int(change),
            "change_pct": change_pct,
            "mktcap": int(mktcap) if mktcap else None,
            "shares": int(shares) if shares else None,
            "trading_date": date.today().strftime("%Y%m%d"),
        }
        ttl = 0.1 if _is_kr_trading_hours() else 6  # 장중 6분, 장외 6시간
        set_cached(cache_key, result, ttl_hours=ttl)
        # 영속 캐시 write-through
        try:
            from .stock_info_store import upsert_price
            upsert_price(code, "KR", result)
        except Exception:
            pass
        return result

    except Exception as e:
        raise RuntimeError(f"시세 조회 실패 ({code}): {e}") from e


def fetch_detail(code: str, refresh: bool = False) -> Optional[dict]:
    """info 커맨드용 상세정보: 시장구분, 업종, 52주 고저, PER, PBR 추가."""
    cache_key = f"market:detail:{code}"
    if refresh:
        delete_prefix(f"market:detail:{code}")
        delete_prefix(f"market:kr_yf_ticker:{code}")
    else:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None

    price = fetch_price(code, refresh=refresh)
    if price is None:
        return None

    try:
        t = _ticker(ticker_str)
        fi = t.fast_info
        info = t.info

        market_type = _market_type(ticker_str)
        sector = info.get("sector")  # 영문
        high_52 = fi.year_high
        low_52 = fi.year_low
        per_raw = info.get("trailingPE") or info.get("forwardPE")
        pbr_raw = info.get("priceToBook")

        result = {
            **price,
            "market_type": market_type,
            "sector": sector,
            "high_52": int(high_52) if high_52 else None,
            "low_52": int(low_52) if low_52 else None,
            "per": round(per_raw, 2) if per_raw else None,
            "pbr": round(pbr_raw, 2) if pbr_raw else None,
        }
        set_cached(cache_key, result, ttl_hours=6)
        return result

    except Exception as e:
        raise RuntimeError(f"상세정보 조회 실패 ({code}): {e}") from e


def _fetch_valuation_history_yf_kr(code: str, years: int) -> list[dict]:
    """KRX 인증 없을 때 yfinance로 국내 종목 PER/PBR 히스토리 추정.

    fetch_valuation_history_yf()와 동일한 로직. .KS/.KQ ticker 자동 선택.
    결과를 market:val_hist 캐시에도 저장하여 일관된 응답 보장.
    """
    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return []
    try:
        from stock.yf_client import fetch_valuation_history_yf
        result = fetch_valuation_history_yf(ticker_str, min(years, 5))
        if result:
            cache_key = f"market:val_hist:{code}:{years}"
            set_cached(cache_key, result, ttl_hours=24)
        return result
    except Exception:
        return []


def fetch_valuation_history(code: str, years: int = 10) -> list[dict]:
    """월말 기준 PER/PBR 히스토리 반환.

    pykrx get_market_fundamental 사용. KRX 인증(KRX_ID/KRX_PASSWORD) 필요.
    미인증 또는 조회 실패 시 yfinance(분기 EPS/BPS + 일별 주가)로 fallback.
    """
    cache_key = f"market:val_hist:{code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # KRX 인증 시도
    try:
        from screener.krx_auth import ensure_krx_session
        if not ensure_krx_session():
            return _fetch_valuation_history_yf_kr(code, years)
    except Exception:
        return _fetch_valuation_history_yf_kr(code, years)

    from pykrx import stock as krx
    import pandas as pd

    end = date.today()
    start = date(end.year - years, end.month, end.day)

    try:
        df = krx.get_market_fundamental(
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            code,
        )
    except Exception:
        return _fetch_valuation_history_yf_kr(code, years)

    if df is None or df.empty:
        return _fetch_valuation_history_yf_kr(code, years)

    # 시가총액 계산용: 종가 + 발행주식수
    try:
        ohlcv = krx.get_market_ohlcv_by_date(
            start.strftime("%Y%m%d"), end.strftime("%Y%m%d"), code
        )
    except Exception:
        ohlcv = pd.DataFrame()

    shares_current = None
    shares_series = None
    try:
        ticker_str = _kr_yf_ticker_str(code)
        if ticker_str:
            import yfinance as yf
            t_yf = yf.Ticker(ticker_str)
            shares_current = int(t_yf.fast_info.shares or 0) or None
            qbs = t_yf.quarterly_balance_sheet
            if qbs is not None and not qbs.empty:
                for name in ("Ordinary Shares Number", "Share Issued"):
                    if name in qbs.index:
                        shares_series = qbs.loc[name].dropna().sort_index()
                        break
    except Exception:
        pass

    # 월말 기준 리샘플 (pandas 2.2+: "ME", 이전: "M")
    try:
        df = df.resample("ME").last()
    except Exception:
        df = df.resample("M").last()

    # 종가 월말 리샘플
    close_monthly = {}
    if not ohlcv.empty and "종가" in ohlcv.columns:
        try:
            cm = ohlcv["종가"].resample("ME").last().dropna()
        except Exception:
            cm = ohlcv["종가"].resample("M").last().dropna()
        close_monthly = {ts.strftime("%Y-%m"): float(v) for ts, v in cm.items()}

    result = []
    for dt, row in df.iterrows():
        per_val = row.get("PER", 0)
        pbr_val = row.get("PBR", 0)
        per = round(float(per_val), 2) if per_val and float(per_val) not in (0.0,) else None
        pbr = round(float(pbr_val), 2) if pbr_val and float(pbr_val) not in (0.0,) else None
        if per is None and pbr is None:
            continue
        date_label = dt.strftime("%Y-%m")
        close = close_monthly.get(date_label)
        # 해당 월 기준 발행주식수 (분기별 시계열에서 최근값)
        shares = shares_current
        if shares_series is not None and len(shares_series) > 0:
            dt_naive = dt.tz_localize(None) if hasattr(dt, 'tz_localize') and dt.tzinfo else dt
            past_s = shares_series[shares_series.index <= dt_naive]
            if len(past_s) >= 1:
                shares = int(past_s.iloc[-1])
        mktcap = round(close * shares) if close and shares else None
        result.append({
            "date": date_label,
            "per": per,
            "pbr": pbr,
            "mktcap": mktcap,
            "shares": int(shares) if shares else None,
        })

    set_cached(cache_key, result, ttl_hours=24)
    return result


def fetch_market_metrics(code: str) -> dict:
    """잔고 페이지용 시가총액·PER·PBR·ROE·배당수익률 단일 종목 조회 (52주 고저 없음).

    반환: {mktcap(원), per, pbr, roe(%, None 가능), market_type, dividend_yield(%)}
    """
    cache_key = f"market:metrics:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    result: dict = {
        "market_type": None,
        "mktcap": None,
        "shares": None,
        "per": None,
        "pbr": None,
        "roe": None,
        "dividend_yield": None,
        "dividend_per_share": None,
    }

    if not ticker_str:
        set_cached(cache_key, result, ttl_hours=1)
        return result

    try:
        t = _ticker(ticker_str)
        fi = t.fast_info
        info = t.info

        result["market_type"] = _market_type(ticker_str)
        result["mktcap"] = int(fi.market_cap) if fi.market_cap else None
        result["shares"] = int(fi.shares) if fi.shares else None
        result["high_52"] = int(fi.year_high) if fi.year_high else None
        result["low_52"] = int(fi.year_low) if fi.year_low else None

        per_raw = info.get("trailingPE") or info.get("forwardPE")
        pbr_raw = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")
        # dividendYield: 이미 % 형태 (0.4, 1.3) → 우선 사용
        # trailingAnnualDividendYield: 소수점 형태 → ×100 변환 (ADR 오계산 가능)
        # dividendRate(연간 주당배당금) ÷ 현재가 → 마지막 fallback
        div_yield_pct  = info.get("dividendYield")
        trailing_yield = info.get("trailingAnnualDividendYield")
        div_rate       = info.get("dividendRate")
        price_now      = fi.last_price
        if div_yield_pct is not None:
            div_yield = round(float(div_yield_pct), 2)
        elif trailing_yield is not None:
            div_yield = round(trailing_yield * 100, 2)
        elif div_rate and price_now and price_now > 0:
            computed = float(div_rate) / float(price_now) * 100
            div_yield = round(computed, 2) if 0 < computed < 50 else None
        else:
            div_yield = None

        div_per_share_raw = info.get("dividendRate")  # 연간 주당배당금 (원)
        result["per"] = round(per_raw, 2) if per_raw else None
        result["pbr"] = round(pbr_raw, 2) if pbr_raw else None
        # PBR fallback: priceToBook이 None이면 자본총계/주식수로 직접 계산
        if result["pbr"] is None and fi.last_price and fi.shares:
            try:
                qbs = t.quarterly_balance_sheet
                if qbs is not None and not qbs.empty:
                    for eq_name in ("Stockholders Equity", "Common Stock Equity"):
                        if eq_name in qbs.index:
                            eq_val = float(qbs.loc[eq_name].dropna().iloc[0])
                            if eq_val > 0:
                                bps = eq_val / fi.shares
                                result["pbr"] = round(fi.last_price / bps, 2)
                            break
            except Exception:
                pass
        result["roe"] = round(roe_raw * 100, 2) if roe_raw else None
        result["dividend_yield"] = div_yield
        result["dividend_per_share"] = round(float(div_per_share_raw)) if div_per_share_raw else None

    except Exception:
        pass

    ttl = 1 if _is_kr_trading_hours() else 12  # 장중 1시간, 장외 12시간
    set_cached(cache_key, result, ttl_hours=ttl)
    # 영속 캐시 write-through
    try:
        from .stock_info_store import upsert_metrics
        upsert_metrics(code, "KR", result)
    except Exception:
        pass
    return result


def fetch_period_returns(code: str) -> dict:
    """당일/3개월/6개월/1년 주가 수익률 반환 (%).

    반환: {change_pct, return_3m, return_6m, return_1y}
    각 값은 None 가능 (데이터 없을 때)
    """
    cache_key = f"market:period_returns:{code}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from .yf_client import _ticker

    ticker_str = _kr_yf_ticker_str(code)
    empty = {
        "change_pct": None,
        "return_3m": None,
        "return_6m": None,
        "return_1y": None,
    }

    if not ticker_str:
        return empty

    try:
        hist = _ticker(ticker_str).history(period="14mo")
    except Exception:
        return empty

    if hist is None or hist.empty:
        return empty

    # tz-aware 인덱스를 tz-naive로 변환
    try:
        hist.index = hist.index.tz_convert(None)
    except Exception:
        hist.index = hist.index.tz_localize(None)

    df = hist[["Close"]].copy().sort_index()
    current_close = float(df["Close"].iloc[-1])

    if len(df) >= 2:
        prev_val = float(df["Close"].iloc[-2])
        day_pct = round((current_close - prev_val) / prev_val * 100, 2) if prev_val else None
    else:
        day_pct = None

    today = pd.Timestamp.today().normalize()

    def get_past_close(days: int) -> Optional[float]:
        target = today - pd.Timedelta(days=days)
        subset = df[df.index <= target]
        return float(subset["Close"].iloc[-1]) if not subset.empty else None

    def pct(past: Optional[float]) -> Optional[float]:
        if past is None or past == 0:
            return None
        return round((current_close - past) / abs(past) * 100, 1)

    result = {
        "change_pct": day_pct,
        "return_3m": pct(get_past_close(90)),
        "return_6m": pct(get_past_close(180)),
        "return_1y": pct(get_past_close(365)),
    }
    ttl = 0.25 if _is_kr_trading_hours() else 6  # 장중 15분, 장외 6시간
    set_cached(cache_key, result, ttl_hours=ttl)
    # 영속 캐시 write-through
    try:
        from .stock_info_store import upsert_returns
        upsert_returns(code, "KR", result)
    except Exception:
        pass
    return result

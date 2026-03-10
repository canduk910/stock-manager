"""국내 주식 시세 · 시가총액 · 52주 고저 조회 — yfinance 기반.

pykrx KRX 스크래핑이 2026-02-27 이후 KRX 서버 변경(로그인 필수화)으로
동작 불가해짐. yfinance (.KS KOSPI / .KQ KOSDAQ suffix)로 대체.

제약사항:
  - PER / PBR: yfinance 국내 주식 미지원 → None 반환
  - 밸류에이션 히스토리: 미지원 → 빈 배열 반환
  - 섹터명: 영문 반환
"""

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .cache import delete_prefix, get_cached, set_cached


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

    import yfinance as yf

    best: Optional[str] = None
    best_score = -1  # 0=가격만, 1=가격+시총, 2=가격+시총+shares

    for suffix in [".KS", ".KQ"]:
        try:
            fi = yf.Ticker(f"{code}{suffix}").fast_info
            price = fi.last_price
            if not price or price <= 0:
                continue
            score = 0
            if fi.market_cap:
                score += 1
            if fi.shares:
                score += 1
            if score > best_score:
                best = f"{code}{suffix}"
                best_score = score
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

    import yfinance as yf

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None

    try:
        fi = yf.Ticker(ticker_str).fast_info

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
        set_cached(cache_key, result, ttl_hours=1)
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

    import yfinance as yf

    ticker_str = _kr_yf_ticker_str(code)
    if not ticker_str:
        return None

    price = fetch_price(code, refresh=refresh)
    if price is None:
        return None

    try:
        t = yf.Ticker(ticker_str)
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


def fetch_valuation_history(code: str, years: int = 10) -> list[dict]:
    """월말 기준 PER/PBR 히스토리 반환.

    pykrx get_market_fundamental 사용. KRX 인증(KRX_ID/KRX_PASSWORD) 필요.
    미인증 또는 조회 실패 시 빈 배열 반환.
    """
    cache_key = f"market:val_hist:{code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # KRX 인증 시도
    try:
        from screener.krx_auth import ensure_krx_session
        if not ensure_krx_session():
            return []
    except Exception:
        return []

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
        return []

    if df is None or df.empty:
        return []

    # 월말 기준 리샘플 (pandas 2.2+: "ME", 이전: "M")
    try:
        df = df.resample("ME").last()
    except Exception:
        df = df.resample("M").last()

    result = []
    for dt, row in df.iterrows():
        per_val = row.get("PER", 0)
        pbr_val = row.get("PBR", 0)
        per = round(float(per_val), 2) if per_val and float(per_val) not in (0.0,) else None
        pbr = round(float(pbr_val), 2) if pbr_val and float(pbr_val) not in (0.0,) else None
        if per is None and pbr is None:
            continue
        result.append({
            "date": dt.strftime("%Y-%m"),
            "per": per,
            "pbr": pbr,
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

    import yfinance as yf

    ticker_str = _kr_yf_ticker_str(code)
    result: dict = {
        "market_type": None,
        "mktcap": None,
        "per": None,
        "pbr": None,
        "roe": None,
        "dividend_yield": None,
    }

    if not ticker_str:
        set_cached(cache_key, result, ttl_hours=1)
        return result

    try:
        t = yf.Ticker(ticker_str)
        fi = t.fast_info
        info = t.info

        result["market_type"] = _market_type(ticker_str)
        result["mktcap"] = int(fi.market_cap) if fi.market_cap else None

        per_raw = info.get("trailingPE") or info.get("forwardPE")
        pbr_raw = info.get("priceToBook")
        roe_raw = info.get("returnOnEquity")
        # dividendYield: 이미 % 형태 (0.4, 1.3), KR/US 공통 → 우선 사용
        # trailingAnnualDividendYield: 소수점 형태이나 외국 ADR에서 오계산 가능 → fallback
        div_yield_pct  = info.get("dividendYield")
        trailing_yield = info.get("trailingAnnualDividendYield")
        if div_yield_pct is not None:
            div_yield = round(float(div_yield_pct), 2)
        elif trailing_yield is not None:
            div_yield = round(trailing_yield * 100, 2)
        else:
            div_yield = None

        result["per"] = round(per_raw, 2) if per_raw else None
        result["pbr"] = round(pbr_raw, 2) if pbr_raw else None
        result["roe"] = round(roe_raw * 100, 2) if roe_raw else None
        result["dividend_yield"] = div_yield

    except Exception:
        pass

    set_cached(cache_key, result, ttl_hours=6)
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

    import yfinance as yf

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
        hist = yf.Ticker(ticker_str).history(period="14mo")
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
    set_cached(cache_key, result, ttl_hours=1)
    return result

"""pykrx 기반 시세 · 시가총액 · 52주 고저 조회."""

from datetime import date, timedelta
from typing import Optional

import pandas as pd

from .cache import delete_prefix, get_cached, set_cached


def _latest_trading_date() -> str:
    """실제 체결 데이터가 있는 가장 최근 거래일 반환 (YYYYMMDD).

    get_market_ticker_list는 비거래일도 반환하므로 삼성전자(005930) 종가가
    0이 아닌 날을 기준으로 거래일을 판별한다.
    """
    cache_key = "market:trading_date"
    cached = get_cached(cache_key)
    if cached:
        return cached

    from pykrx import stock as krx

    d = date.today() - timedelta(days=1)
    for _ in range(14):  # 공휴일 연속 최대 10일 이상 여유
        ds = d.strftime("%Y%m%d")
        try:
            df = krx.get_market_ohlcv_by_ticker(ds, market="KOSPI")
            if "005930" in df.index and int(df.loc["005930", "종가"]) > 0:
                set_cached(cache_key, ds, ttl_hours=6)
                return ds
        except Exception:
            pass
        d -= timedelta(days=1)

    fallback = (date.today() - timedelta(days=1)).strftime("%Y%m%d")
    return fallback


def fetch_price(code: str, refresh: bool = False) -> Optional[dict]:
    """
    현재가, 전일대비(%), 시가총액, 상장주식수 조회.
    반환: dict 또는 None (종목 없음)
    """
    cache_key = f"market:price:{code}"
    if refresh:
        delete_prefix(f"market:price:{code}")
    else:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    from pykrx import stock as krx

    trading_date = _latest_trading_date()

    try:
        df_ohlcv = krx.get_market_ohlcv_by_ticker(trading_date, market="ALL")
        if code not in df_ohlcv.index:
            return None

        row = df_ohlcv.loc[code]
        close = int(row["종가"])
        change_pct = float(row.get("등락률", 0))

        df_cap = krx.get_market_cap_by_ticker(trading_date, market="ALL")
        mktcap = int(df_cap.loc[code, "시가총액"]) if code in df_cap.index else None
        shares = int(df_cap.loc[code, "상장주식수"]) if code in df_cap.index else None

        # 절대 등락액: close * change_pct / (100 + change_pct)
        change = round(close * change_pct / (100 + change_pct)) if (100 + change_pct) != 0 else 0

        result = {
            "code": code,
            "close": close,
            "change": change,
            "change_pct": change_pct,
            "mktcap": mktcap,
            "shares": shares,
            "trading_date": trading_date,
        }
        set_cached(cache_key, result)
        return result

    except Exception as e:
        raise RuntimeError(f"시세 조회 실패 ({code}): {e}") from e


def fetch_detail(code: str, refresh: bool = False) -> Optional[dict]:
    """
    info 커맨드용 상세정보: 시장구분, 업종, 52주 고저 추가.
    """
    cache_key = f"market:detail:{code}"
    if refresh:
        delete_prefix(f"market:detail:{code}")
    else:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    from pykrx import stock as krx

    price = fetch_price(code, refresh=refresh)
    if price is None:
        return None

    trading_date = price["trading_date"]

    # 52주 고저
    one_year_ago = (date.today() - timedelta(days=365)).strftime("%Y%m%d")
    try:
        df_year = krx.get_market_ohlcv_by_date(one_year_ago, trading_date, code)
        high_52 = int(df_year["고가"].max()) if not df_year.empty else None
        low_52 = int(df_year["저가"].min()) if not df_year.empty else None
    except Exception:
        high_52 = low_52 = None

    # 시장구분 + 업종
    market_type = None
    sector = None
    try:
        kospi_tickers = krx.get_market_ticker_list(trading_date, market="KOSPI")
        market_type = "KOSPI" if code in kospi_tickers else "KOSDAQ"
        sector_df = krx.get_market_sector_classifications(trading_date, market=market_type)
        if code in sector_df.index:
            sector = sector_df.loc[code, "업종명"]
    except Exception:
        pass

    # PER / PBR
    per, pbr = None, None
    try:
        df_fund = krx.get_market_fundamental_by_ticker(trading_date, market="ALL")
        if code in df_fund.index:
            per_raw = float(df_fund.loc[code, "PER"])
            pbr_raw = float(df_fund.loc[code, "PBR"])
            per = per_raw if per_raw > 0 else None
            pbr = pbr_raw if pbr_raw > 0 else None
    except Exception:
        pass

    result = {
        **price,
        "market_type": market_type,
        "sector": sector,
        "high_52": high_52,
        "low_52": low_52,
        "per": per,
        "pbr": pbr,
    }
    set_cached(cache_key, result)
    return result


def fetch_valuation_history(code: str, years: int = 10) -> list[dict]:
    """월말 기준 PER/PBR 히스토리 반환.

    반환: [{"date": "2024-01", "per": 12.5, "pbr": 1.2}, ...]  # 과거 → 최신 순
    """
    cache_key = f"market:valuation_hist:{code}:{years}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    from pykrx import stock as krx

    end_dt = date.today()
    start_dt = end_dt.replace(year=end_dt.year - years)
    end_str = end_dt.strftime("%Y%m%d")
    start_str = start_dt.strftime("%Y%m%d")

    try:
        df = krx.get_market_fundamental_by_date(start_str, end_str, code)
    except Exception:
        return []

    if df.empty:
        return []

    df.index = pd.to_datetime(df.index)
    # 월말 마지막 거래일 기준으로 리샘플
    df_monthly = df.resample("ME").last()

    result = []
    for dt, row in df_monthly.iterrows():
        per_val = float(row.get("PER", 0) or 0)
        pbr_val = float(row.get("PBR", 0) or 0)
        if per_val <= 0 and pbr_val <= 0:
            continue
        result.append({
            "date": dt.strftime("%Y-%m"),
            "per": round(per_val, 2) if per_val > 0 else None,
            "pbr": round(pbr_val, 2) if pbr_val > 0 else None,
        })

    set_cached(cache_key, result, ttl_hours=24)
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

    from pykrx import stock as krx

    today = date.today()
    one_year_ago = today - timedelta(days=370)  # 여유 있게 370일
    end_str = today.strftime("%Y%m%d")
    start_str = one_year_ago.strftime("%Y%m%d")

    try:
        df = krx.get_market_ohlcv_by_date(start_str, end_str, code)
    except Exception:
        return {"change_pct": None, "return_3m": None, "return_6m": None, "return_1y": None}

    if df is None or df.empty:
        return {"change_pct": None, "return_3m": None, "return_6m": None, "return_1y": None}

    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    current_close = float(df["종가"].iloc[-1])

    # 당일 등락률: 최근 2 거래일 비교
    if len(df) >= 2:
        prev_close = float(df["종가"].iloc[-2])
        day_pct = round((current_close - prev_close) / prev_close * 100, 2) if prev_close else None
    else:
        day_pct = None

    def get_past_close(days: int) -> Optional[float]:
        target = pd.Timestamp(today - timedelta(days=days))
        subset = df[df.index <= target]
        return float(subset["종가"].iloc[-1]) if not subset.empty else None

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

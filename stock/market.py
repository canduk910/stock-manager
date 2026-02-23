"""pykrx 기반 시세 · 시가총액 · 52주 고저 조회."""

from datetime import date, timedelta
from typing import Optional

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

        result = {
            "code": code,
            "close": close,
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

    result = {
        **price,
        "market_type": market_type,
        "sector": sector,
        "high_52": high_52,
        "low_52": low_52,
    }
    set_cached(cache_key, result)
    return result

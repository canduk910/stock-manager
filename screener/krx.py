"""KRX(한국거래소) 데이터 수집 모듈.

pykrx 라이브러리를 사용하여 전종목 시세, 시가총액, PER/PBR/EPS/BPS를 수집한다.
ROE는 EPS/BPS로 산출한다.
"""

from pykrx import stock

from .cache import get_cached, set_cached


def get_all_stocks(date_str: str) -> list[dict]:
    """전종목 시세 + 펀더멘털 통합 데이터 반환.

    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열

    Returns:
        list of dict with keys:
            code, name, market, per, pbr, roe, mktcap
    """
    cache_key = f"stocks_merged:{date_str}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # 시장별 종목코드 집합
    try:
        kospi_tickers = set(stock.get_market_ticker_list(date_str, market="KOSPI"))
        kosdaq_tickers = set(stock.get_market_ticker_list(date_str, market="KOSDAQ"))
    except Exception as e:
        raise RuntimeError(f"KRX 종목 목록 조회 실패: {e}") from e

    if not kospi_tickers and not kosdaq_tickers:
        raise RuntimeError(
            f"{date_str} 날짜의 KRX 데이터가 없습니다. "
            "거래일이 맞는지 확인해주세요."
        )

    # 펀더멘털 데이터 (PER, PBR, EPS, BPS)
    try:
        fund_df = stock.get_market_fundamental(date_str, market="ALL")
    except Exception as e:
        raise RuntimeError(f"KRX 펀더멘털 데이터 조회 실패: {e}") from e

    # 시가총액 데이터
    try:
        cap_df = stock.get_market_cap(date_str, market="ALL")
    except Exception as e:
        raise RuntimeError(f"KRX 시가총액 데이터 조회 실패: {e}") from e

    # 종목명 조회
    all_tickers = kospi_tickers | kosdaq_tickers
    ticker_names: dict[str, str] = {}
    for t in all_tickers:
        try:
            ticker_names[t] = stock.get_market_ticker_name(t)
        except Exception:
            ticker_names[t] = ""

    stocks = []
    for ticker in all_tickers:
        name = ticker_names.get(ticker, "")
        market_name = "KOSPI" if ticker in kospi_tickers else "KOSDAQ"

        # 펀더멘털
        per = None
        pbr = None
        roe = None
        if ticker in fund_df.index:
            row = fund_df.loc[ticker]
            per_val = float(row.get("PER", 0))
            pbr_val = float(row.get("PBR", 0))
            eps_val = float(row.get("EPS", 0))
            bps_val = float(row.get("BPS", 0))

            per = per_val if per_val != 0.0 else None
            pbr = pbr_val if pbr_val != 0.0 else None

            if bps_val != 0.0:
                roe = round(eps_val / bps_val * 100, 2)

        # 시가총액
        mktcap = 0
        if ticker in cap_df.index:
            mktcap = int(cap_df.loc[ticker, "시가총액"])

        stocks.append(
            {
                "code": ticker,
                "name": name,
                "market": market_name,
                "per": per,
                "pbr": pbr,
                "roe": roe,
                "mktcap": mktcap,
            }
        )

    set_cached(cache_key, stocks)
    return stocks

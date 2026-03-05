"""KRX(한국거래소) 데이터 수집 모듈.

pykrx 라이브러리를 사용하여 전종목 시세, 시가총액, PER/PBR/EPS/BPS를 수집한다.
ROE는 EPS/BPS로 산출한다.
"""

from datetime import datetime, timedelta

from pykrx import stock

from .cache import get_cached, set_cached


_KRX_DOWN_MSG = (
    "KRX 데이터 서비스가 일시적으로 이용 불가합니다.\n"
    "2026년 2월 27일부터 한국거래소(KRX)가 데이터 서비스를 회원제로 전환하여 "
    "pykrx 기반 스크리닝이 현재 동작하지 않습니다.\n"
    "pykrx 라이브러리 업데이트를 기다려 주세요: https://github.com/sharebook-kr/pykrx/issues/276"
)


def _find_latest_trading_day(date_str: str) -> str:
    """주어진 날짜 또는 그 이전의 가장 최근 거래일(데이터 있는 날)을 반환.

    최대 10일 전까지 소급하여 탐색한다.
    """
    dt = datetime.strptime(date_str, "%Y%m%d")
    for _ in range(10):
        candidate = dt.strftime("%Y%m%d")
        try:
            tickers = stock.get_market_ticker_list(candidate, market="KOSPI")
            if tickers:
                return candidate
        except Exception:
            pass
        dt -= timedelta(days=1)
    return date_str  # fallback: 원래 날짜 그대로


def get_all_stocks(date_str: str) -> list[dict]:
    """전종목 시세 + 펀더멘털 통합 데이터 반환.

    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열.
                  해당 날짜에 데이터가 없으면(주말/공휴일) 가장 최근 거래일로 자동 소급.

    Returns:
        list of dict with keys:
            code, name, market, per, pbr, roe, mktcap
    """
    # 실제 사용할 거래일 결정 (주말/공휴일이면 이전 거래일로 소급)
    trading_date = _find_latest_trading_day(date_str)

    cache_key = f"stocks_merged:{trading_date}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    # 시장별 종목코드 집합
    try:
        kospi_tickers = set(stock.get_market_ticker_list(trading_date, market="KOSPI"))
        kosdaq_tickers = set(stock.get_market_ticker_list(trading_date, market="KOSDAQ"))
    except Exception as e:
        raise RuntimeError(_KRX_DOWN_MSG) from e

    if not kospi_tickers and not kosdaq_tickers:
        raise RuntimeError(_KRX_DOWN_MSG)

    # 펀더멘털 데이터 (PER, PBR, EPS, BPS)
    try:
        fund_df = stock.get_market_fundamental(trading_date, market="ALL")
    except Exception as e:
        raise RuntimeError(_KRX_DOWN_MSG) from e

    # 시가총액 데이터
    try:
        cap_df = stock.get_market_cap(trading_date, market="ALL")
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

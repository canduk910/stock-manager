"""KRX(한국거래소) 데이터 수집 모듈.

pykrx 라이브러리를 사용하여 전종목 시세, 시가총액, PER/PBR/EPS/BPS를 수집한다.
ROE는 EPS/BPS로 산출한다.

인증:
    2026-02-27부터 KRX 서버가 로그인 필수로 전환됨.
    KRX_ID / KRX_PASSWORD 환경변수를 설정하면 자동 로그인 후 정상 동작.
    미설정 시 스크리닝 불가 (친절한 안내 메시지 반환).
"""

from datetime import datetime, timedelta

from pykrx import stock

from .cache import get_cached, set_cached
from .krx_auth import ensure_krx_session, is_krx_configured


_KRX_NO_AUTH_MSG = (
    "KRX 로그인 정보가 설정되지 않았습니다.\n"
    "2026년 2월 27일부터 한국거래소(KRX)가 데이터 서비스를 로그인 필수로 전환했습니다.\n"
    "환경변수 KRX_ID / KRX_PASSWORD 를 설정하면 스크리닝이 정상 동작합니다.\n"
    "(KRX 회원가입: https://data.krx.co.kr)"
)

_KRX_LOGIN_FAIL_MSG = (
    "KRX 로그인에 실패했습니다.\n"
    "KRX_ID / KRX_PASSWORD 환경변수가 올바른지 확인해주세요.\n"
    "(KRX 회원가입: https://data.krx.co.kr)"
)


def _find_latest_trading_day(date_str: str) -> str:
    """주어진 날짜 이전의 가장 최근 거래일(데이터 있는 날)을 반환.

    1단계: 주말(토·일)은 API 없이 즉시 건너뜀.
    2단계: 공휴일은 pykrx API로 확인 (데이터 없으면 하루씩 소급).
    API가 모두 실패하면 주말만 제거한 날짜를 fallback으로 반환.
    """
    dt = datetime.strptime(date_str, "%Y%m%d")

    # 1단계: 주말 스킵 (API 불필요)
    for _ in range(7):
        if dt.weekday() < 5:  # 0=월 ~ 4=금
            break
        dt -= timedelta(days=1)

    weekday_fallback = dt.strftime("%Y%m%d")

    # 2단계: 공휴일 확인 (API 활용)
    cur = dt
    for _ in range(10):
        candidate = cur.strftime("%Y%m%d")
        try:
            tickers = stock.get_market_ticker_list(candidate, market="KOSPI")
            if tickers:
                return candidate
        except Exception:
            pass
        cur -= timedelta(days=1)
        # 주말 스킵
        while cur.weekday() >= 5:
            cur -= timedelta(days=1)

    return weekday_fallback  # API 실패 시 주말만 제거한 날짜 반환


def get_all_stocks(date_str: str) -> tuple[list[dict], str]:
    """전종목 시세 + 펀더멘털 통합 데이터 반환.

    Args:
        date_str: YYYYMMDD 형식의 날짜 문자열.
                  해당 날짜에 데이터가 없으면(주말/공휴일) 가장 최근 거래일로 자동 소급.

    Returns:
        (stocks, actual_date): 종목 목록 + 실제 조회된 거래일(YYYYMMDD)

    Raises:
        RuntimeError: KRX 미인증 또는 로그인 실패 시.
    """
    # KRX 인증 확인
    if not is_krx_configured():
        raise RuntimeError(_KRX_NO_AUTH_MSG)
    if not ensure_krx_session():
        raise RuntimeError(_KRX_LOGIN_FAIL_MSG)

    # 실제 사용할 거래일 결정 (주말/공휴일이면 이전 거래일로 소급)
    trading_date = _find_latest_trading_day(date_str)

    cache_key = f"stocks_merged:{trading_date}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached, trading_date

    # 시장별 종목코드 집합
    try:
        kospi_tickers = set(stock.get_market_ticker_list(trading_date, market="KOSPI"))
        kosdaq_tickers = set(stock.get_market_ticker_list(trading_date, market="KOSDAQ"))
    except Exception as e:
        raise RuntimeError(f"KRX 종목 목록 조회 실패: {e}") from e

    if not kospi_tickers and not kosdaq_tickers:
        raise RuntimeError("KRX에서 종목 목록을 가져올 수 없습니다. 로그인 세션을 확인해주세요.")

    # 펀더멘털 데이터 (PER, PBR, EPS, BPS)
    try:
        fund_df = stock.get_market_fundamental(trading_date, market="ALL")
    except Exception as e:
        raise RuntimeError(f"KRX 펀더멘탈 데이터 조회 실패: {e}") from e

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
    return stocks, trading_date

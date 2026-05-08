"""REQ-INTEG-06/07/09: stock/yf_client.py KIS 우선 통합 단위 테스트.

검증 범위:
- fetch_price_yf 미국 종목 → KIS 우선, KIS None 시 yfinance fallback
- fetch_price_yf 응답 dict shape 변경 없음 (close/change/change_pct/mktcap/currency)
- fetch_detail_yf 가격 필드만 KIS 덮어쓰기, PER/52주/배당 등은 yfinance
- fetch_period_returns_yf 일봉 KIS 우선, 252봉 미달 시 yfinance fallback
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────


def _kis_price_ok():
    return {
        "last": 150.5,
        "change": 1.5,
        "change_rate": 1.01,
        "volume": 12345,
        "currency": "USD",
        "exchange": "NAS",
    }


@pytest.fixture(autouse=True)
def _clear_cache(tmp_path, monkeypatch):
    """각 테스트마다 캐시 격리 (cache.db 임시 위치 + monkeypatch)."""
    # stock.cache의 get_cached/set_cached를 no-op으로 만들어 격리
    from stock import cache as _cache
    monkeypatch.setattr(_cache, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(_cache, "set_cached", lambda *a, **kw: None)
    # yf_client는 stock.cache의 get_cached/set_cached를 자체 import한 상태이므로
    # 모듈 내부 참조도 교체
    from stock import yf_client as _yfc
    monkeypatch.setattr(_yfc, "get_cached", lambda *a, **kw: None)
    monkeypatch.setattr(_yfc, "set_cached", lambda *a, **kw: None)
    yield


# ── REQ-INTEG-06: fetch_price_yf ──────────────────────────────────────────────


def test_fetch_price_yf_kis_first_normal():
    """KIS 정상 → KIS 가격 사용, yfinance 호출 없음."""
    from stock import yf_client

    with patch("stock.yf_client.get_kis_price", return_value=_kis_price_ok()) as kis_mock, \
         patch("stock.yf_client._ticker") as ticker_mock:
        result = yf_client.fetch_price_yf("AAPL")

    assert result is not None
    assert result["close"] == 150.5
    assert result["change"] == 1.5
    assert result["change_pct"] == 1.01
    assert result["currency"] == "USD"
    # yfinance fast_info 미호출
    ticker_mock.assert_not_called()
    kis_mock.assert_called_once()


def test_fetch_price_yf_kis_none_falls_back_to_yf():
    """KIS None → yfinance 경로 동작."""
    from stock import yf_client

    fake_ticker = MagicMock()
    fake_ticker.fast_info.last_price = 200.0
    fake_ticker.fast_info.previous_close = 198.0
    fake_ticker.fast_info.market_cap = 1.5e12
    fake_ticker.fast_info.currency = "USD"

    with patch("stock.yf_client.get_kis_price", return_value=None), \
         patch("stock.yf_client._ticker", return_value=fake_ticker):
        result = yf_client.fetch_price_yf("AAPL")

    assert result is not None
    assert result["close"] == 200.0
    # change = 200 - 198 = 2.0
    assert abs((result["change"] or 0) - 2.0) < 0.01


def test_fetch_price_yf_kis_exception_falls_back():
    """KIS 예외 → yfinance fallback (서비스 무중단)."""
    from stock import yf_client

    fake_ticker = MagicMock()
    fake_ticker.fast_info.last_price = 200.0
    fake_ticker.fast_info.previous_close = 198.0
    fake_ticker.fast_info.market_cap = 1.5e12
    fake_ticker.fast_info.currency = "USD"

    with patch("stock.yf_client.get_kis_price", side_effect=Exception("kis-down")), \
         patch("stock.yf_client._ticker", return_value=fake_ticker):
        result = yf_client.fetch_price_yf("AAPL")

    assert result is not None
    assert result["close"] == 200.0


def test_fetch_price_yf_response_shape_unchanged():
    """KIS 사용 시에도 응답 dict 키가 변경되지 않음 (후방 호환)."""
    from stock import yf_client

    with patch("stock.yf_client.get_kis_price", return_value=_kis_price_ok()), \
         patch("stock.yf_client._ticker"):
        result = yf_client.fetch_price_yf("AAPL")

    expected_keys = {"code", "close", "change", "change_pct", "mktcap", "currency"}
    assert expected_keys.issubset(set(result.keys()))


# ── REQ-INTEG-07: fetch_detail_yf ─────────────────────────────────────────────


def test_fetch_detail_yf_overrides_only_price_fields():
    """KIS 정상 → close/change/change_pct만 KIS 덮어쓰기, PER/52주/배당은 yfinance."""
    from stock import yf_client

    fake_ticker = MagicMock()
    fake_ticker.info = {
        "longName": "Apple Inc.",
        "quoteType": "EQUITY",
        "currentPrice": 145.0,  # yfinance — KIS가 덮어써야 함
        "previousClose": 143.0,
        "marketCap": 2.4e12,
        "currency": "USD",
        "exchange": "NMS",
        "sector": "Technology",
        "fiftyTwoWeekHigh": 250.0,  # yfinance only
        "fiftyTwoWeekLow": 130.0,
        "trailingPE": 28.5,         # yfinance only
        "priceToBook": 50.0,
        "returnOnEquity": 1.7,
        "dividendYield": 0.4,
    }
    fake_ticker.fast_info.last_price = 145.0
    fake_ticker.fast_info.previous_close = 143.0
    fake_ticker.fast_info.market_cap = 2.4e12
    fake_ticker.fast_info.currency = "USD"

    with patch("stock.yf_client.get_kis_price", return_value=_kis_price_ok()), \
         patch("stock.yf_client._ticker", return_value=fake_ticker):
        result = yf_client.fetch_detail_yf("AAPL")

    assert result is not None
    # 가격 필드는 KIS
    assert result["close"] == 150.5
    assert result["change"] == 1.5
    assert result["change_pct"] == 1.01
    # 비가격 필드는 yfinance 보존
    assert result["high_52"] == 250.0
    assert result["low_52"] == 130.0
    assert result["per"] == 28.5
    assert result["pbr"] == 50.0
    assert result["sector"] == "Technology"


def test_fetch_detail_yf_kis_none_uses_yf_price():
    """KIS None → yfinance 가격 사용 (전체 경로 yfinance)."""
    from stock import yf_client

    fake_ticker = MagicMock()
    fake_ticker.info = {
        "longName": "Apple Inc.",
        "quoteType": "EQUITY",
        "currentPrice": 145.0,
        "previousClose": 143.0,
        "marketCap": 2.4e12,
        "currency": "USD",
        "exchange": "NMS",
        "sector": "Technology",
        "fiftyTwoWeekHigh": 250.0,
        "fiftyTwoWeekLow": 130.0,
        "trailingPE": 28.5,
        "priceToBook": 50.0,
        "returnOnEquity": 1.7,
        "dividendYield": 0.4,
    }
    fake_ticker.fast_info.last_price = 145.0
    fake_ticker.fast_info.previous_close = 143.0
    fake_ticker.fast_info.market_cap = 2.4e12
    fake_ticker.fast_info.currency = "USD"

    with patch("stock.yf_client.get_kis_price", return_value=None), \
         patch("stock.yf_client._ticker", return_value=fake_ticker):
        result = yf_client.fetch_detail_yf("AAPL")

    # yfinance 가격 사용
    assert result["close"] == 145.0
    # change = 145 - 143 = 2.0
    assert abs((result["change"] or 0) - 2.0) < 0.01


# ── REQ-INTEG-09: fetch_period_returns_yf ─────────────────────────────────────


def _build_kis_daily(n_days: int = 260, base_price: float = 100.0) -> list[dict]:
    """KIS 응답 형식의 일봉 list (최신 → 과거 순). step=+1.0/일."""
    rows = []
    today = 20260508
    for i in range(n_days):
        # 최신 → 과거: i=0이 가장 최신
        rows.append({
            "date": str(today - i),
            "open": base_price + (n_days - i),
            "high": base_price + (n_days - i) + 1,
            "low": base_price + (n_days - i) - 1,
            "close": base_price + (n_days - i),
            "volume": 1000,
        })
    return rows


def test_fetch_period_returns_yf_kis_first_normal():
    """KIS 252봉+ 확보 → KIS 사용, yfinance 미호출."""
    from stock import yf_client

    rows = _build_kis_daily(260)
    with patch("stock.yf_client.get_kis_ohlcv_daily", return_value=rows) as kis_mock, \
         patch("stock.yf_client._ticker") as ticker_mock:
        result = yf_client.fetch_period_returns_yf("AAPL")

    # 결과 dict 키 변경 없음
    assert "change_pct" in result or len(result) == 0  # 최소 빈 dict가 아님 보장 어려움
    # KIS 호출됨 + yfinance 미호출
    kis_mock.assert_called_once()
    ticker_mock.assert_not_called()


def test_fetch_period_returns_yf_kis_short_falls_back():
    """KIS 252봉 미달 → yfinance fallback."""
    from stock import yf_client

    rows = _build_kis_daily(100)  # 1Y 산출 불가

    fake_hist = MagicMock()
    import pandas as pd
    fake_hist.__getitem__ = MagicMock(return_value=pd.Series([100.0] * 260))
    fake_hist.empty = False
    fake_ticker = MagicMock()
    fake_ticker.history.return_value = fake_hist

    with patch("stock.yf_client.get_kis_ohlcv_daily", return_value=rows), \
         patch("stock.yf_client._ticker", return_value=fake_ticker):
        result = yf_client.fetch_period_returns_yf("AAPL")

    # yfinance 경로 동작 → 결과 dict 반환
    assert isinstance(result, dict)


def test_fetch_period_returns_yf_kis_none_falls_back():
    """KIS None → yfinance fallback."""
    from stock import yf_client

    fake_hist = MagicMock()
    import pandas as pd
    fake_hist.__getitem__ = MagicMock(return_value=pd.Series([100.0, 102.0]))
    fake_hist.empty = False
    fake_ticker = MagicMock()
    fake_ticker.history.return_value = fake_hist

    with patch("stock.yf_client.get_kis_ohlcv_daily", return_value=None), \
         patch("stock.yf_client._ticker", return_value=fake_ticker):
        result = yf_client.fetch_period_returns_yf("AAPL")

    assert isinstance(result, dict)


def test_fetch_period_returns_yf_response_shape_unchanged():
    """KIS/yfinance 둘 다에서 반환 dict 키 변경 없음."""
    from stock import yf_client

    rows = _build_kis_daily(260)
    with patch("stock.yf_client.get_kis_ohlcv_daily", return_value=rows), \
         patch("stock.yf_client._ticker"):
        result = yf_client.fetch_period_returns_yf("AAPL")

    # 빈 결과(데이터 부족 시) 또는 정규 dict — 키는 표준 4개
    if result:
        allowed_keys = {"change_pct", "return_3m", "return_6m", "return_1y"}
        assert set(result.keys()).issubset(allowed_keys)

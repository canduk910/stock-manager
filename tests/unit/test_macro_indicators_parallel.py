"""QW-2: fetch_macro_indicators 병렬화 검증.

7심볼(국채/금/유가/환율/달러인덱스/VIX)을 ThreadPoolExecutor로 병렬 조회.
일부 실패 시 부분 응답 보존(None 채움). 캐시 hit 시 ThreadPool 미생성.
"""

from unittest.mock import MagicMock, patch

import pytest


_EXPECTED_KEYS = {
    "us_10y_yield", "gold", "oil_wti",
    "usd_krw", "usd_jpy", "dollar_index", "vix",
}


class _FakeFastInfo:
    def __init__(self, last_price=None, previous_close=None):
        self.last_price = last_price
        self.previous_close = previous_close


def _make_ticker(price):
    """fast_info.last_price=price 인 가짜 Ticker."""
    t = MagicMock()
    t.fast_info = _FakeFastInfo(last_price=price, previous_close=None)
    return t


class TestFetchMacroIndicatorsParallel:
    def test_all_symbols_succeed(self):
        from stock import yf_client

        with patch.object(yf_client, "get_cached", return_value=None), \
             patch.object(yf_client, "set_cached"), \
             patch.object(yf_client, "_ticker", side_effect=lambda sym: _make_ticker(100.0)):
            result = yf_client.fetch_macro_indicators()

        assert set(result.keys()) == _EXPECTED_KEYS
        assert all(v == 100.0 for v in result.values())

    def test_partial_failure_other_symbols_preserved(self):
        """1개 심볼이 raise해도 나머지는 정상 채움."""
        from stock import yf_client

        def _ticker_side(sym):
            if sym == "GC=F":
                raise RuntimeError("yf failure")
            return _make_ticker(50.0)

        with patch.object(yf_client, "get_cached", return_value=None), \
             patch.object(yf_client, "set_cached"), \
             patch.object(yf_client, "_ticker", side_effect=_ticker_side):
            result = yf_client.fetch_macro_indicators()

        assert set(result.keys()) == _EXPECTED_KEYS
        assert result["gold"] is None
        assert result["us_10y_yield"] == 50.0
        assert result["vix"] == 50.0

    def test_cache_hit_skips_ticker_calls(self):
        """캐시 hit 시 _ticker / ThreadPool 미호출."""
        from stock import yf_client

        cached = {k: 1.0 for k in _EXPECTED_KEYS}
        ticker_mock = MagicMock(side_effect=AssertionError("should not be called"))

        with patch.object(yf_client, "get_cached", return_value=cached), \
             patch.object(yf_client, "_ticker", ticker_mock):
            result = yf_client.fetch_macro_indicators()

        assert result == cached
        ticker_mock.assert_not_called()

    def test_uses_threadpool_executor(self):
        """병렬 실행 검증 — ThreadPoolExecutor가 import/사용된다."""
        from stock import yf_client
        import inspect

        # fetch_macro_indicators 본문에 ThreadPoolExecutor 사용 흔적 확인
        src = inspect.getsource(yf_client.fetch_macro_indicators)
        assert "ThreadPoolExecutor" in src or "as_completed" in src, (
            "fetch_macro_indicators must use ThreadPoolExecutor for parallel fetch"
        )

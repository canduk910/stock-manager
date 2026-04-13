"""유틸리티 함수 단위 테스트."""

from stock.utils import is_domestic


class TestIsDomestic:
    def test_six_digit_is_domestic(self):
        assert is_domestic("005930") is True
        assert is_domestic("035720") is True

    def test_us_ticker_is_not_domestic(self):
        assert is_domestic("AAPL") is False
        assert is_domestic("MSFT") is False
        assert is_domestic("NVDA") is False

    def test_fno_code_is_not_domestic(self):
        assert is_domestic("101S6000") is False

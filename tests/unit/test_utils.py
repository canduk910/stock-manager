"""유틸리티 함수 단위 테스트."""

import pytest

from stock.utils import is_domestic, is_fno


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

    def test_empty_string(self):
        assert is_domestic("") is False

    def test_five_digits(self):
        assert is_domestic("12345") is False

    def test_seven_digits(self):
        assert is_domestic("1234567") is False


class TestIsFno:
    def test_index_futures(self):
        assert is_fno("101S6") is True
        assert is_fno("101S6000") is True

    def test_index_options(self):
        assert is_fno("201S6") is True

    def test_stock_futures(self):
        assert is_fno("301S6") is True

    def test_short_code_under_4(self):
        assert is_fno("1A") is False

    def test_six_digit_number_is_not_fno(self):
        assert is_fno("123456") is False

    def test_empty_string(self):
        assert is_fno("") is False

    def test_none_input(self):
        assert is_fno(None) is False

    def test_four_digit_starting_with_other(self):
        assert is_fno("4ABC") is False
        assert is_fno("9XYZ") is False

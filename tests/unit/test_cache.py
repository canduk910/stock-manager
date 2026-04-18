"""stock/cache.py _sanitize 함수 단위 테스트."""

import math

from stock.cache import _sanitize


class TestSanitize:
    def test_nan_to_none(self):
        assert _sanitize(float("nan")) is None

    def test_inf_to_none(self):
        assert _sanitize(float("inf")) is None

    def test_neg_inf_to_none(self):
        assert _sanitize(float("-inf")) is None

    def test_nested_dict_nan(self):
        result = _sanitize({"a": float("nan"), "b": 1.0})
        assert result == {"a": None, "b": 1.0}

    def test_nested_list_nan(self):
        result = _sanitize([float("nan"), 1.0, float("inf")])
        assert result == [None, 1.0, None]

    def test_deeply_nested(self):
        result = _sanitize({"a": {"b": [float("nan"), {"c": float("inf")}]}})
        assert result == {"a": {"b": [None, {"c": None}]}}

    def test_normal_float(self):
        assert _sanitize(3.14) == 3.14

    def test_string_passthrough(self):
        assert _sanitize("hello") == "hello"

    def test_none_passthrough(self):
        assert _sanitize(None) is None

    def test_int_passthrough(self):
        assert _sanitize(42) == 42

    def test_bool_passthrough(self):
        assert _sanitize(True) is True

    def test_empty_dict(self):
        assert _sanitize({}) == {}

    def test_empty_list(self):
        assert _sanitize([]) == []

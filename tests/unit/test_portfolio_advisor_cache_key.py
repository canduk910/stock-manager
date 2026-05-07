"""portfolio_advisor._compute_cache_key 코멘트 통합 검증.

R3 RED:
- 동일 balance + 다른 코멘트 → 다른 키
- 동일 balance + None 코멘트 vs "" 빈 문자열 → 같은 키 (strip)
- 동일 balance + 같은 코멘트 → 같은 키
- 코멘트 미전달(기본값 None) → 코멘트 미사용 시와 동일 키 (백워드)
- 코멘트 strip 양 끝 공백
"""

from __future__ import annotations


def _balance_a() -> dict:
    return {
        "stock_list": [{"code": "005930", "quantity": 10}],
        "overseas_list": [{"code": "AAPL", "quantity": 5}],
    }


def _balance_b() -> dict:
    return {
        "stock_list": [{"code": "005930", "quantity": 10}],
        "overseas_list": [{"code": "MSFT", "quantity": 5}],
    }


class TestPortfolioCacheKeyUserComment:
    def test_different_comment_different_key(self):
        from services.portfolio_advisor_service import _compute_cache_key
        k1 = _compute_cache_key(_balance_a(), user_comment="국내 비중 늘려야 한다")
        k2 = _compute_cache_key(_balance_a(), user_comment="해외 비중 늘려야 한다")
        assert k1 != k2

    def test_none_vs_empty_string_same_key(self):
        from services.portfolio_advisor_service import _compute_cache_key
        k1 = _compute_cache_key(_balance_a(), user_comment=None)
        k2 = _compute_cache_key(_balance_a(), user_comment="")
        assert k1 == k2

    def test_none_vs_whitespace_same_key(self):
        from services.portfolio_advisor_service import _compute_cache_key
        k1 = _compute_cache_key(_balance_a(), user_comment=None)
        k2 = _compute_cache_key(_balance_a(), user_comment="   ")
        assert k1 == k2

    def test_default_arg_backward_compat(self):
        from services.portfolio_advisor_service import _compute_cache_key
        # 기존 코드 (코멘트 없는 호출) 과 새 호출 (None) 동일 키
        k1 = _compute_cache_key(_balance_a())
        k2 = _compute_cache_key(_balance_a(), user_comment=None)
        assert k1 == k2

    def test_same_comment_same_key(self):
        from services.portfolio_advisor_service import _compute_cache_key
        k1 = _compute_cache_key(_balance_a(), user_comment="동일 코멘트")
        k2 = _compute_cache_key(_balance_a(), user_comment="동일 코멘트")
        assert k1 == k2

    def test_different_balance_different_key(self):
        """balance만 달라도 다른 키 (회귀 보호)."""
        from services.portfolio_advisor_service import _compute_cache_key
        k1 = _compute_cache_key(_balance_a(), user_comment="x")
        k2 = _compute_cache_key(_balance_b(), user_comment="x")
        assert k1 != k2

    def test_comment_strip_whitespace(self):
        """앞뒤 공백 strip — 의미상 동일한 코멘트는 같은 키."""
        from services.portfolio_advisor_service import _compute_cache_key
        k1 = _compute_cache_key(_balance_a(), user_comment="가설")
        k2 = _compute_cache_key(_balance_a(), user_comment="  가설  ")
        assert k1 == k2

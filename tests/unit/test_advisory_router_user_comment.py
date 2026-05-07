"""routers/advisory.py + routers/portfolio_advisor.py 사용자 코멘트 검증 로직 단위 테스트.

Docker(PostgreSQL) 비의존 — 라우터 핸들러 함수를 직접 호출해 1000자 검증 + 코멘트 정규화를
검증한다. API 통합(TestClient)은 tests/api/test_advisory_analyze_with_comment.py에서 다룸.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from services.exceptions import ServiceError


def _fake_user() -> dict:
    return {"id": 1, "username": "test", "role": "user"}


class TestAdvisoryAnalyzeRouterValidation:
    def test_long_comment_raises_service_error(self):
        from routers.advisory import analyze, AnalyzeBody
        body = AnalyzeBody(user_comment="x" * 1001)
        with patch("routers.advisory.advisory_store") as store_mock:
            store_mock.get_stock.return_value = None
            with pytest.raises(ServiceError) as exc:
                analyze("005930", body=body, market="KR", user=_fake_user())
            assert "1000자" in str(exc.value)

    def test_no_body_passes_none(self):
        from routers.advisory import analyze
        from services import advisory_service
        with patch("routers.advisory.advisory_store") as store_mock, \
             patch.object(advisory_service, "generate_ai_report",
                          return_value={"id": 1}) as gen_mock:
            store_mock.get_stock.return_value = None
            result = analyze("005930", body=None, market="KR", user=_fake_user())
            _, kwargs = gen_mock.call_args
            assert kwargs.get("user_comment") is None
            assert result == {"id": 1}

    def test_with_body_passes_comment(self):
        from routers.advisory import analyze, AnalyzeBody
        from services import advisory_service
        with patch("routers.advisory.advisory_store") as store_mock, \
             patch.object(advisory_service, "generate_ai_report",
                          return_value={"id": 2}) as gen_mock:
            store_mock.get_stock.return_value = None
            analyze("005930", body=AnalyzeBody(user_comment="가설"),
                    market="KR", user=_fake_user())
            _, kwargs = gen_mock.call_args
            assert kwargs.get("user_comment") == "가설"

    def test_whitespace_only_normalized_to_none(self):
        from routers.advisory import analyze, AnalyzeBody
        from services import advisory_service
        with patch("routers.advisory.advisory_store") as store_mock, \
             patch.object(advisory_service, "generate_ai_report",
                          return_value={"id": 3}) as gen_mock:
            store_mock.get_stock.return_value = None
            analyze("005930", body=AnalyzeBody(user_comment="   "),
                    market="KR", user=_fake_user())
            _, kwargs = gen_mock.call_args
            assert kwargs.get("user_comment") is None

    def test_exactly_1000_chars_ok(self):
        from routers.advisory import analyze, AnalyzeBody
        from services import advisory_service
        text = "가" * 1000
        with patch("routers.advisory.advisory_store") as store_mock, \
             patch.object(advisory_service, "generate_ai_report",
                          return_value={"id": 4}) as gen_mock:
            store_mock.get_stock.return_value = None
            analyze("005930", body=AnalyzeBody(user_comment=text),
                    market="KR", user=_fake_user())
            _, kwargs = gen_mock.call_args
            assert kwargs.get("user_comment") == text


class TestPortfolioAnalyzeRouterValidation:
    def _balance(self) -> dict:
        return {"stock_list": [{"code": "005930", "quantity": 10}], "overseas_list": []}

    def test_long_comment_raises_service_error(self):
        from routers.portfolio_advisor import analyze, AnalyzeBody
        body = AnalyzeBody(
            balance_data=self._balance(),
            force_refresh=False,
            user_comment="x" * 1001,
        )
        with pytest.raises(ServiceError):
            analyze(body, _user=_fake_user())

    def test_no_comment_passes_none(self):
        from routers.portfolio_advisor import analyze, AnalyzeBody
        from services import portfolio_advisor_service
        body = AnalyzeBody(balance_data=self._balance(), force_refresh=False)
        with patch.object(portfolio_advisor_service, "analyze_portfolio",
                          return_value={"data": {}}) as an_mock:
            analyze(body, _user=_fake_user())
            _, kwargs = an_mock.call_args
            assert kwargs.get("user_comment") is None

    def test_with_comment_passes_through(self):
        from routers.portfolio_advisor import analyze, AnalyzeBody
        from services import portfolio_advisor_service
        body = AnalyzeBody(
            balance_data=self._balance(),
            force_refresh=False,
            user_comment="성장주 늘려야 한다",
        )
        with patch.object(portfolio_advisor_service, "analyze_portfolio",
                          return_value={"data": {}}) as an_mock:
            analyze(body, _user=_fake_user())
            _, kwargs = an_mock.call_args
            assert kwargs.get("user_comment") == "성장주 늘려야 한다"

"""portfolio_advisor_service.chat_with_report 단위 테스트."""

from unittest.mock import patch, MagicMock

import pytest

from services import portfolio_advisor_service as svc
from services.exceptions import NotFoundError, ServiceError


def _fake_portfolio_row():
    return {
        "id": 7,
        "report": {
            "diagnosis": {"summary": "방어적 포지션"},
            "rebalance": [{"code": "005930", "action": "trim"}],
            "trades": [],
            "market_comment": "buffett=mid",
            "schema_version": "v2",
        },
        "model": "gpt-5.4",
    }


def _ai_resp(text="..."):
    msg = MagicMock(); msg.content = text
    choice = MagicMock(); choice.message = msg; choice.finish_reason = "stop"
    resp = MagicMock(); resp.choices = [choice]; resp.model = "gpt-5.4"
    return resp


class TestPortfolioChatValidation:
    def test_empty_messages_rejected(self):
        with patch.object(svc, "OPENAI_API_KEY", "x"):
            with pytest.raises(ServiceError):
                svc.chat_with_report(7, [], user_id=1)


class TestPortfolioChatLookup:
    def test_missing_report_404(self):
        with patch.object(svc, "OPENAI_API_KEY", "x"), \
             patch.object(svc.advisory_store, "get_portfolio_report_by_id",
                          return_value=None):
            with pytest.raises(NotFoundError):
                svc.chat_with_report(
                    999, [{"role": "user", "content": "?"}], user_id=1,
                )


class TestPortfolioChatHappyPath:
    def test_system_prompt_includes_report_sections(self):
        with patch.object(svc, "OPENAI_API_KEY", "x"), \
             patch.object(svc.advisory_store, "get_portfolio_report_by_id",
                          return_value=_fake_portfolio_row()), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp("ok")) as m:
            result = svc.chat_with_report(
                7, [{"role": "user", "content": "리밸런싱 의도는?"}], user_id=1,
            )
        assert result["reply"] == "ok"
        assert result["report_id"] == 7
        kwargs = m.call_args.kwargs
        assert kwargs["service_name"] == "portfolio_chat"
        sys = kwargs["messages"][0]["content"]
        # 보고서 섹션 키워드가 system prompt에 직렬화되어 들어감
        assert "diagnosis" in sys
        assert "rebalance" in sys
        assert "trades" in sys

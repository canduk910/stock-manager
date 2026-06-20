"""advisory_service.chat_with_report 단위 테스트."""

from unittest.mock import patch, MagicMock

import pytest

from services import advisory_service
from services import advisory_chat  # chat_with_report 분리 모듈 (2026-06-20)
from services.exceptions import NotFoundError, ServiceError


def _fake_report_row(user_id=1, code="005930", market="KR"):
    return {
        "id": 100,
        "user_id": user_id,
        "code": code,
        "market": market,
        "name": "삼성전자",
        "report": {"종합의견": "B+ 등급, 보유 권고", "schema_version": "v3"},
        "model": "gpt-5.4",
    }


def _ai_resp(text: str = "보고서에 따르면 ..."):
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    resp = MagicMock()
    resp.choices = [choice]
    resp.model = "gpt-5.4"
    return resp


class TestChatValidation:
    def test_empty_messages_rejected(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"):
            with pytest.raises(ServiceError):
                advisory_service.chat_with_report("005930", "KR", 100, [], user_id=1)

    def test_last_message_must_be_user(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"):
            with pytest.raises(ServiceError):
                advisory_service.chat_with_report(
                    "005930", "KR", 100,
                    [{"role": "user", "content": "안녕"},
                     {"role": "assistant", "content": "안녕하세요"}],
                    user_id=1,
                )

    def test_invalid_role_rejected(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"):
            with pytest.raises(ServiceError):
                advisory_service.chat_with_report(
                    "005930", "KR", 100,
                    [{"role": "system", "content": "x"}],
                    user_id=1,
                )

    def test_empty_content_rejected(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"):
            with pytest.raises(ServiceError):
                advisory_service.chat_with_report(
                    "005930", "KR", 100,
                    [{"role": "user", "content": "  "}],
                    user_id=1,
                )

    def test_too_long_content_rejected(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"):
            with pytest.raises(ServiceError):
                advisory_service.chat_with_report(
                    "005930", "KR", 100,
                    [{"role": "user", "content": "x" * 4001}],
                    user_id=1,
                )


def _make_user_filtered_lookup(owner_user_id: int = 1, code: str = "005930", market: str = "KR"):
    """Repository가 user_id 필터링하는 동작을 시뮬레이션한 mock 헬퍼."""
    def _lookup(report_id, user_id=None):
        if user_id is not None and user_id != owner_user_id:
            return None
        return _fake_report_row(user_id=owner_user_id, code=code, market=market)
    return _lookup


class TestChatReportLookup:
    def test_missing_report_404(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id", return_value=None):
            with pytest.raises(NotFoundError):
                advisory_service.chat_with_report(
                    "005930", "KR", 999,
                    [{"role": "user", "content": "안전마진?"}],
                    user_id=1,
                )

    def test_other_user_report_404(self):
        # Repository가 user_id 필터링하므로 타 유저 호출 시 None 반환
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id",
                          side_effect=_make_user_filtered_lookup(owner_user_id=2)):
            with pytest.raises(NotFoundError):
                advisory_service.chat_with_report(
                    "005930", "KR", 100,
                    [{"role": "user", "content": "안전마진?"}],
                    user_id=1,
                )

    def test_get_report_by_id_called_with_user_id(self):
        """챗봇 호출 시 Repository에 user_id가 전달되어 권한 필터링되는지 확인."""
        with patch.object(advisory_chat, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id",
                          return_value=_fake_report_row()) as m, \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp()):
            advisory_service.chat_with_report(
                "005930", "KR", 100,
                [{"role": "user", "content": "?"}],
                user_id=1,
            )
        # 호출 인자 검증: report_id=100, user_id=1
        args, kwargs = m.call_args
        assert args[0] == 100
        assert kwargs.get("user_id") == 1

    def test_mismatched_code_404(self):
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id",
                          side_effect=_make_user_filtered_lookup(code="005930")):
            with pytest.raises(NotFoundError):
                advisory_service.chat_with_report(
                    "000660", "KR", 100,
                    [{"role": "user", "content": "?"}],
                    user_id=1,
                )


class TestChatHappyPath:
    def test_returns_reply_and_calls_gateway(self):
        with patch.object(advisory_chat, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id",
                          return_value=_fake_report_row()), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp("등급은 B+입니다.")) as m:
            result = advisory_service.chat_with_report(
                "005930", "KR", 100,
                [{"role": "user", "content": "등급이 뭐야?"}],
                user_id=1,
            )
        assert result["reply"] == "등급은 B+입니다."
        assert result["report_id"] == 100
        kwargs = m.call_args.kwargs
        assert kwargs["service_name"] == "advisory_chat"
        assert kwargs["user_id"] == 1
        assert kwargs["max_completion_tokens"] == 1500
        sent = kwargs["messages"]
        assert sent[0]["role"] == "system"
        assert "보고서" in sent[0]["content"]
        assert sent[-1] == {"role": "user", "content": "등급이 뭐야?"}


class TestChatSlidingWindow:
    def test_keeps_last_20_messages(self):
        many = [{"role": "user" if i % 2 == 0 else "assistant",
                 "content": f"m{i}"} for i in range(30)]
        many[-1] = {"role": "user", "content": "마지막 질문"}
        with patch.object(advisory_chat, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id",
                          return_value=_fake_report_row()), \
             patch("services.ai_gateway.call_openai_chat", return_value=_ai_resp()) as m:
            advisory_service.chat_with_report(
                "005930", "KR", 100, many, user_id=1,
            )
        sent = m.call_args.kwargs["messages"]
        # system + 최근 20개
        assert len(sent) == 21
        assert sent[0]["role"] == "system"
        assert sent[-1]["content"] == "마지막 질문"

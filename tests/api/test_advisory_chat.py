"""POST /api/advisory/{code}/chat 엔드포인트 테스트."""

from unittest.mock import patch, MagicMock


def _ai_resp(text="ok"):
    msg = MagicMock(); msg.content = text
    choice = MagicMock(); choice.message = msg; choice.finish_reason = "stop"
    resp = MagicMock(); resp.choices = [choice]; resp.model = "gpt-5.4"
    return resp


class TestAdvisoryChatEndpoint:
    def test_chat_missing_report_404(self, client):
        body = {"market": "KR", "report_id": 999999,
                "messages": [{"role": "user", "content": "안전마진?"}]}
        resp = client.post("/api/advisory/005930/chat", json=body)
        assert resp.status_code == 404

    def test_chat_empty_messages_400(self, client):
        body = {"market": "KR", "report_id": 1, "messages": []}
        resp = client.post("/api/advisory/005930/chat", json=body)
        # Pydantic은 빈 list를 허용하므로 service 단에서 400 ServiceError
        assert resp.status_code == 400

    def test_chat_missing_report_id_422(self, client):
        body = {"market": "KR", "messages": [{"role": "user", "content": "x"}]}
        resp = client.post("/api/advisory/005930/chat", json=body)
        assert resp.status_code == 422

    def test_chat_last_message_assistant_400(self, client):
        body = {
            "market": "KR", "report_id": 1,
            "messages": [
                {"role": "user", "content": "안녕"},
                {"role": "assistant", "content": "안녕하세요"},
            ],
        }
        resp = client.post("/api/advisory/005930/chat", json=body)
        # report_id 1 존재하지 않을 가능성 → 404, 또는 검증 단계 400
        assert resp.status_code in (400, 404)

    def test_chat_ok_when_mocked(self, client):
        from services import advisory_service
        fake_row = {
            "id": 100, "user_id": 1, "code": "005930", "market": "KR",
            "name": "삼성전자", "report": {"등급": "B+"}, "model": "gpt-5.4",
        }
        with patch.object(advisory_service, "OPENAI_API_KEY", "x"), \
             patch.object(advisory_service.advisory_store, "get_report_by_id",
                          return_value=fake_row), \
             patch("services.ai_gateway.call_openai_chat",
                   return_value=_ai_resp("등급은 B+입니다.")):
            body = {"market": "KR", "report_id": 100,
                    "messages": [{"role": "user", "content": "등급?"}]}
            resp = client.post("/api/advisory/005930/chat", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "등급은 B+입니다."
        assert data["report_id"] == 100

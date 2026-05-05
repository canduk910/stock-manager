"""POST /api/portfolio-advisor/chat 엔드포인트 테스트."""

from unittest.mock import patch, MagicMock


def _ai_resp(text="ok"):
    msg = MagicMock(); msg.content = text
    choice = MagicMock(); choice.message = msg; choice.finish_reason = "stop"
    resp = MagicMock(); resp.choices = [choice]; resp.model = "gpt-5.4"
    return resp


class TestPortfolioChatEndpoint:
    def test_missing_report_404(self, client):
        body = {"report_id": 999999,
                "messages": [{"role": "user", "content": "?"}]}
        resp = client.post("/api/portfolio-advisor/chat", json=body)
        assert resp.status_code == 404

    def test_empty_messages_400(self, client):
        body = {"report_id": 1, "messages": []}
        resp = client.post("/api/portfolio-advisor/chat", json=body)
        assert resp.status_code == 400

    def test_chat_ok_when_mocked(self, client):
        from services import portfolio_advisor_service as svc
        fake_row = {
            "id": 5, "report": {"diagnosis": {"summary": "x"}, "rebalance": []},
            "model": "gpt-5.4",
        }
        with patch.object(svc, "OPENAI_API_KEY", "x"), \
             patch.object(svc.advisory_store, "get_portfolio_report_by_id",
                          return_value=fake_row), \
             patch("services.ai_gateway.call_openai_chat",
                   return_value=_ai_resp("진단 요약은 x입니다.")):
            body = {"report_id": 5,
                    "messages": [{"role": "user", "content": "진단?"}]}
            resp = client.post("/api/portfolio-advisor/chat", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "진단 요약은 x입니다."
        assert data["report_id"] == 5

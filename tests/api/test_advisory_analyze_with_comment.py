"""POST /api/advisory/{code}/analyze 사용자 코멘트 전파 테스트.

R2 RED → GREEN:
- body {"user_comment": "..."} → 서비스에 user_comment 인자 전달 → 200
- body 없이 호출 → 200 (백워드 호환, Body(None))
- 1001자 user_comment → 400 (ServiceError)
"""

from unittest.mock import patch, MagicMock


def _fake_report() -> dict:
    return {"id": 1, "code": "005930", "market": "KR", "report": {"등급": "B+"}}


class TestAnalyzeWithUserComment:
    def test_analyze_with_comment_200(self, client):
        """body.user_comment 전달 시 서비스에 user_comment kwarg 전파."""
        from services import advisory_service
        with patch.object(advisory_service, "generate_ai_report",
                          return_value=_fake_report()) as mock_gen:
            body = {"user_comment": "이 종목은 AI 사이클 수혜로 강세"}
            resp = client.post(
                "/api/advisory/005930/analyze?market=KR",
                json=body,
            )
        assert resp.status_code == 200
        # 서비스 호출 인자 검증
        _, kwargs = mock_gen.call_args
        assert kwargs.get("user_comment") == "이 종목은 AI 사이클 수혜로 강세"

    def test_analyze_no_body_backward_compat(self, client):
        """body 없이 호출도 200 (백워드 호환)."""
        from services import advisory_service
        with patch.object(advisory_service, "generate_ai_report",
                          return_value=_fake_report()) as mock_gen:
            resp = client.post("/api/advisory/005930/analyze?market=KR")
        assert resp.status_code == 200
        _, kwargs = mock_gen.call_args
        # 코멘트 없으면 None 전달
        assert kwargs.get("user_comment") is None

    def test_analyze_empty_string_normalized_to_none(self, client):
        """빈 코멘트는 None으로 정규화 (캐시 키 일관성)."""
        from services import advisory_service
        with patch.object(advisory_service, "generate_ai_report",
                          return_value=_fake_report()) as mock_gen:
            resp = client.post(
                "/api/advisory/005930/analyze?market=KR",
                json={"user_comment": "   "},
            )
        assert resp.status_code == 200
        _, kwargs = mock_gen.call_args
        assert kwargs.get("user_comment") is None

    def test_analyze_long_comment_400(self, client):
        """1001자 코멘트 → 400 (ServiceError "1000자 이내")."""
        from services import advisory_service
        long_text = "가" * 1001
        # 서비스가 호출되지 않아야 함 (라우터에서 검증)
        with patch.object(advisory_service, "generate_ai_report") as mock_gen:
            resp = client.post(
                "/api/advisory/005930/analyze?market=KR",
                json={"user_comment": long_text},
            )
        # ServiceError → 400
        assert resp.status_code == 400
        mock_gen.assert_not_called()

    def test_analyze_exactly_1000_chars_ok(self, client):
        """경계값: 1000자 정확히는 통과."""
        from services import advisory_service
        text = "가" * 1000
        with patch.object(advisory_service, "generate_ai_report",
                          return_value=_fake_report()) as mock_gen:
            resp = client.post(
                "/api/advisory/005930/analyze?market=KR",
                json={"user_comment": text},
            )
        assert resp.status_code == 200
        _, kwargs = mock_gen.call_args
        assert kwargs.get("user_comment") == text


class TestPortfolioAnalyzeWithUserComment:
    """R3 포트폴리오 자문 코멘트 전파."""

    def _balance(self) -> dict:
        return {
            "stock_list": [{"code": "005930", "quantity": 10}],
            "overseas_list": [],
        }

    def test_portfolio_analyze_with_comment_200(self, client):
        from services import portfolio_advisor_service
        fake = {"data": {"diagnosis": {}}, "cached": False, "analyzed_at": "2026-05-07"}
        with patch.object(portfolio_advisor_service, "analyze_portfolio",
                          return_value=fake) as mock_an:
            body = {
                "balance_data": self._balance(),
                "force_refresh": False,
                "user_comment": "성장주 비중을 늘려야 한다",
            }
            resp = client.post("/api/portfolio-advisor/analyze", json=body)
        assert resp.status_code == 200
        _, kwargs = mock_an.call_args
        assert kwargs.get("user_comment") == "성장주 비중을 늘려야 한다"

    def test_portfolio_analyze_no_comment_backward(self, client):
        """user_comment 미전달 → user_comment=None."""
        from services import portfolio_advisor_service
        fake = {"data": {}, "cached": False, "analyzed_at": "2026-05-07"}
        with patch.object(portfolio_advisor_service, "analyze_portfolio",
                          return_value=fake) as mock_an:
            body = {"balance_data": self._balance(), "force_refresh": False}
            resp = client.post("/api/portfolio-advisor/analyze", json=body)
        assert resp.status_code == 200
        _, kwargs = mock_an.call_args
        assert kwargs.get("user_comment") is None

    def test_portfolio_analyze_long_comment_400(self, client):
        from services import portfolio_advisor_service
        long_text = "가" * 1001
        with patch.object(portfolio_advisor_service, "analyze_portfolio") as mock_an:
            body = {
                "balance_data": self._balance(),
                "force_refresh": False,
                "user_comment": long_text,
            }
            resp = client.post("/api/portfolio-advisor/analyze", json=body)
        assert resp.status_code == 400
        mock_an.assert_not_called()

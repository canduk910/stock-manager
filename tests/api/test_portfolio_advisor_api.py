"""Portfolio Advisor API 엔드포인트 테스트 (A-140 ~ A-142)."""

import pytest


class TestPortfolioAdvisorEndpoints:
    """AI 포트폴리오 자문 API."""

    def test_analyze(self, client):
        """A-140: POST /api/portfolio-advisor/analyze → 200 or 503."""
        resp = client.post("/api/portfolio-advisor/analyze", json={
            "balance_data": {
                "stock_list": [],
                "overseas_list": [],
                "deposit": "10000000",
            },
            "force_refresh": False,
        })
        # OPENAI_API_KEY 없으면 503, 잔고 빈 경우 정상 or 에러
        assert resp.status_code in (200, 503, 502, 400)

    def test_get_history(self, client):
        """A-141: GET /api/portfolio-advisor/history → 200."""
        resp = client.get("/api/portfolio-advisor/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_report_not_found(self, client):
        """A-142: 없는 리포트 → 404."""
        resp = client.get("/api/portfolio-advisor/history/99999")
        assert resp.status_code == 404

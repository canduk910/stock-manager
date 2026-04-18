"""Macro API 엔드포인트 테스트 (A-080 ~ A-084)."""

import pytest


class TestMacroEndpoints:
    """매크로 분석 API — 섹션별 독립 실패 허용."""

    def test_get_indices(self, client):
        """A-080: GET /api/macro/indices → 200."""
        resp = client.get("/api/macro/indices")
        # yfinance 기반 → 외부 API 실패 가능
        assert resp.status_code in (200, 502)

    def test_get_news(self, client):
        """A-081: GET /api/macro/news → 200."""
        resp = client.get("/api/macro/news")
        assert resp.status_code in (200, 502)

    def test_get_sentiment(self, client):
        """A-082: GET /api/macro/sentiment → 200."""
        resp = client.get("/api/macro/sentiment")
        assert resp.status_code in (200, 502)

    def test_get_investor_quotes(self, client):
        """A-083: GET /api/macro/investor-quotes → 200."""
        resp = client.get("/api/macro/investor-quotes")
        assert resp.status_code in (200, 502)

    def test_get_summary(self, client):
        """A-084: GET /api/macro/summary → 200 (부분 실패 허용)."""
        resp = client.get("/api/macro/summary")
        assert resp.status_code in (200, 502)

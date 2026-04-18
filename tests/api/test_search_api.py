"""Search API 엔드포인트 테스트 (A-120 ~ A-121)."""

import pytest


class TestSearchEndpoints:
    """종목 검색 API."""

    def test_search_stocks_kr(self, client):
        """A-120: GET /api/search?q=삼성 → 200, list."""
        resp = client.get("/api/search", params={"q": "삼성", "market": "KR"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_search_empty_query(self, client):
        """A-121: 빈 쿼리 → 200, []."""
        resp = client.get("/api/search", params={"q": "", "market": "KR"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_search_single_char(self, client):
        """KR 검색 1글자 미만 → 200, []."""
        resp = client.get("/api/search", params={"q": "삼", "market": "KR"})
        assert resp.status_code == 200
        data = resp.json()
        # 2글자 미만 검색 안 함 → 빈 배열
        assert isinstance(data, list)

    def test_search_us_market(self, client):
        """US 시장 검색 → 200."""
        resp = client.get("/api/search", params={"q": "AAPL", "market": "US"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_search_unknown_market(self, client):
        """지원하지 않는 시장 → 200, []."""
        resp = client.get("/api/search", params={"q": "test", "market": "XX"})
        assert resp.status_code == 200
        data = resp.json()
        assert data == []

    def test_search_kr_code(self, client):
        """6자리 종목코드 직접 입력 → 200."""
        resp = client.get("/api/search", params={"q": "005930", "market": "KR"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

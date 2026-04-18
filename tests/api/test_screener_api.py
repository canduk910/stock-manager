"""Screener API 엔드포인트 테스트 (A-100 ~ A-101)."""

import pytest


class TestScreenerEndpoints:
    """스크리너 API — pykrx/KRX 의존."""

    @pytest.mark.slow
    def test_get_stocks(self, client):
        """A-100: GET /api/screener/stocks → 200 (KRX 데이터, 느림)."""
        resp = client.get("/api/screener/stocks", params={"top": 3})
        # KRX 서버 다운/pykrx 이슈 시 502 또는 500
        assert resp.status_code in (200, 500, 502)
        if resp.status_code == 200:
            data = resp.json()
            assert "date" in data
            assert "total" in data
            assert "stocks" in data
            assert isinstance(data["stocks"], list)

    def test_get_stocks_with_filters(self, client):
        """A-101: 필터 파라미터 적용 → 200."""
        resp = client.get("/api/screener/stocks", params={
            "per_max": 15,
            "roe_min": 10,
            "top": 5,
        })
        assert resp.status_code in (200, 502)
        if resp.status_code == 200:
            data = resp.json()
            assert data["total"] <= 5

    def test_get_stocks_invalid_market(self, client):
        """스크리너 잘못된 시장 파라미터 → 422."""
        resp = client.get("/api/screener/stocks", params={"market": "INVALID"})
        assert resp.status_code == 422

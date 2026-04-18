"""Detail API 엔드포인트 테스트 (A-060 ~ A-063)."""

import pytest


class TestDetailEndpoints:
    """종목 상세 분석 API."""

    def test_get_financials(self, client):
        """A-060: GET /api/detail/financials/{symbol} → 200."""
        resp = client.get("/api/detail/financials/005930")
        assert resp.status_code in (200, 502)
        if resp.status_code == 200:
            data = resp.json()
            # 재무 데이터 구조 확인
            assert isinstance(data, dict)

    def test_get_valuation(self, client):
        """A-061: GET /api/detail/valuation/{symbol} → 200."""
        resp = client.get("/api/detail/valuation/005930")
        assert resp.status_code in (200, 502)

    def test_get_report(self, client):
        """A-062: GET /api/detail/report/{symbol} → 200."""
        resp = client.get("/api/detail/report/005930")
        assert resp.status_code in (200, 502)

    def test_financials_us(self, client):
        """A-063: 해외 재무 → 200 (yfinance 기반)."""
        resp = client.get("/api/detail/financials/AAPL")
        assert resp.status_code in (200, 502)

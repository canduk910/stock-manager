"""Earnings API 엔드포인트 테스트 (A-110 ~ A-112)."""

import pytest


class TestEarningsEndpoints:
    """공시(정기보고서) API."""

    def test_get_filings_kr(self, client):
        """A-110: GET /api/earnings/filings?market=KR → 200."""
        resp = client.get("/api/earnings/filings", params={"market": "KR"})
        # OPENDART_API_KEY 미설정 시 502
        assert resp.status_code in (200, 502)
        if resp.status_code == 200:
            data = resp.json()
            assert data["market"] == "KR"
            assert "filings" in data
            assert "total" in data

    def test_get_filings_us(self, client):
        """A-111: GET /api/earnings/filings?market=US → 200 (SEC EDGAR, 키 불필요)."""
        resp = client.get("/api/earnings/filings", params={"market": "US"})
        assert resp.status_code in (200, 502)
        if resp.status_code == 200:
            data = resp.json()
            assert data["market"] == "US"
            assert "filings" in data

    def test_get_filings_date_range(self, client):
        """A-112: 날짜 범위 조회 → 200."""
        resp = client.get("/api/earnings/filings", params={
            "market": "KR",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        })
        assert resp.status_code in (200, 502)

    def test_get_filings_invalid_range(self, client):
        """날짜 범위 초과 (90일) → 422."""
        resp = client.get("/api/earnings/filings", params={
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
        })
        assert resp.status_code == 422

    def test_get_filings_reversed_dates(self, client):
        """종료일 < 시작일 → 422."""
        resp = client.get("/api/earnings/filings", params={
            "start_date": "2026-03-01",
            "end_date": "2026-01-01",
        })
        assert resp.status_code == 422

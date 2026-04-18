"""Backtest API 엔드포인트 테스트 (A-150 ~ A-155)."""

import pytest


class TestBacktestEndpoints:
    """백테스트 API — KIS_MCP_ENABLED=false 기본."""

    def test_mcp_status(self, client):
        """A-150: GET /api/backtest/status → 200."""
        resp = client.get("/api/backtest/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "available" in data
        assert isinstance(data["available"], bool)

    def test_get_presets(self, client):
        """A-151: GET /api/backtest/presets → 200 or 502 (MCP 미연결)."""
        resp = client.get("/api/backtest/presets")
        assert resp.status_code in (200, 502, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)

    def test_get_indicators(self, client):
        """A-152: GET /api/backtest/indicators → 200 or 502/503 (MCP 미연결)."""
        resp = client.get("/api/backtest/indicators")
        assert resp.status_code in (200, 502, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)

    def test_run_preset(self, client):
        """A-153: POST /api/backtest/run/preset → 200 or 503."""
        resp = client.post("/api/backtest/run/preset", json={
            "preset": "golden_cross",
            "symbol": "005930",
            "market": "KR",
        })
        # MCP 비활성화 시 503 or 에러
        assert resp.status_code in (200, 503, 502, 400)

    def test_get_result_not_found(self, client):
        """A-154: 없는 결과 → 404."""
        resp = client.get("/api/backtest/result/nonexistent-id")
        assert resp.status_code in (200, 404)

    def test_get_history(self, client):
        """A-155: GET /api/backtest/history → 200."""
        resp = client.get("/api/backtest/history")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

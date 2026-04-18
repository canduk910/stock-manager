"""Pipeline API 엔드포인트 테스트 (A-130 ~ A-132)."""

import pytest


class TestPipelineEndpoints:
    """투자 파이프라인 API."""

    def test_run_pipeline(self, client):
        """A-130: POST /api/pipeline/run → 200 (비동기 시작)."""
        resp = client.post("/api/pipeline/run", params={"market": "KR"})
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] in ("started", "already_running")

    def test_run_pipeline_invalid_market(self, client):
        """잘못된 시장 → 200 (에러 메시지 포함)."""
        resp = client.post("/api/pipeline/run", params={"market": "XX"})
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    def test_run_pipeline_sync(self, client):
        """A-131: POST /api/pipeline/run-sync → 200 (동기 실행)."""
        resp = client.post("/api/pipeline/run-sync", params={"market": "KR"})
        # 파이프라인 서비스 실행 — 외부 API 실패 가능
        assert resp.status_code in (200, 502)

    def test_get_status(self, client):
        """A-132: GET /api/pipeline/status → 200."""
        resp = client.get("/api/pipeline/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "scheduler" in data
        assert "running" in data

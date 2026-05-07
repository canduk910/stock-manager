"""Backtest local endpoint 입력 검증 테스트.

룰:
  - symbols=[] → Pydantic min_length=1 → 422
  - symbols 11개 → Pydantic max_length=10 → 422
  - 잘못된 preset → 400 (ServiceError)
  - market != "KR" → 400 (ServiceError)
"""

from __future__ import annotations

import pytest


@pytest.fixture
def stub_local_simulate(monkeypatch):
    """엔진은 호출되면 안 됨 — 검증 단계에서 실패해야 함."""
    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("simulate should not be called when validation fails")
    monkeypatch.setattr("services.local_backtest.simulate", _should_not_be_called)
    monkeypatch.setattr("services.local_backtest.engine.simulate", _should_not_be_called)


class TestLocalBacktestValidation:
    def test_empty_symbols_returns_422(self, client, stub_local_simulate):
        """symbols=[] → Pydantic min_length=1 → 422."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "momentum",
            "symbols": [],
            "market": "KR",
        })
        assert resp.status_code == 422

    def test_too_many_symbols_returns_422(self, client, stub_local_simulate):
        """11개 종목 → Pydantic max_length=10 → 422."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "momentum",
            "symbols": [f"00000{i}" for i in range(11)],
            "market": "KR",
        })
        assert resp.status_code == 422

    def test_unknown_preset_returns_400(self, client, stub_local_simulate):
        """알 수 없는 preset → ServiceError → 400."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "no_such_preset",
            "symbols": ["005930"],
            "market": "KR",
        })
        assert resp.status_code == 400

    def test_us_market_returns_400(self, client, stub_local_simulate):
        """market=US → ServiceError → 400."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "momentum",
            "symbols": ["AAPL"],
            "market": "US",
        })
        assert resp.status_code == 400

    def test_inverted_dates_returns_400(self, client, stub_local_simulate):
        """start ≥ end → 400."""
        resp = client.post("/api/backtest/run/local", json={
            "preset": "momentum",
            "symbols": ["005930"],
            "market": "KR",
            "start_date": "2024-12-31",
            "end_date": "2024-01-02",
        })
        assert resp.status_code == 400

    def test_get_local_presets_no_auth_required_for_test_client(self, client):
        """conftest TestClient는 인증 우회 — 200 반환."""
        resp = client.get("/api/backtest/local/presets")
        assert resp.status_code == 200

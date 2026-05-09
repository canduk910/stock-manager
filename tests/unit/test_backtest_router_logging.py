"""REQ-FIX-06: 백테스트 라우터 entry/exit 로그 + ServiceError error_id + telemetry.

수용 기준:
- 라우터 4개(run_local/run_preset/run_custom/run_batch) entry 로그 (preset/symbols/market/dates)
- exit 로그 (job_id/duration_ms/status)
- ServiceError 응답에 `error_id` 8자리 hex 포함 + logger.error 에 동일 id 매칭
- telemetry: `backtest.local.success` / `backtest.local.fail.{cause}` 카운터
"""
from __future__ import annotations

import logging
import re

import pytest

from services import _telemetry as tel
from services import backtest_service


@pytest.fixture(autouse=True)
def _reset_telemetry():
    tel._reset_for_test()
    yield
    tel._reset_for_test()


def _force_local_simulate_success(monkeypatch):
    """run_local_backtest 내부 simulate 와 store 호출을 가짜로 — 외부 의존 제거."""

    class _FakeSim:
        equity_curve = [{"date": "2024-01-01", "equity": 10_000_000}]
        trades = []
        per_symbol_contribution = {}
        params = {}
        failures = []
        metrics = {
            "total_return_pct": 0.0,
            "cagr": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "max_drawdown": 0.0,
            "win_rate": None,
            "profit_factor": None,
            "total_trades": 0,
        }

    def fake_simulate(**kwargs):
        return _FakeSim()

    monkeypatch.setattr(
        "services.local_backtest.simulate", fake_simulate, raising=False
    )
    # backtest_service 내부 import 도 동일 객체 가리킴
    import services.local_backtest as _lb
    monkeypatch.setattr(_lb, "simulate", fake_simulate, raising=False)

    # save_backtest_job / save_backtest_result 가짜
    monkeypatch.setattr(
        backtest_service.strategy_store, "save_backtest_job",
        lambda **kw: {"job_id": kw.get("job_id")},
    )
    monkeypatch.setattr(
        backtest_service.strategy_store, "save_backtest_result",
        lambda **kw: True,
    )
    monkeypatch.setattr(
        backtest_service.strategy_store, "update_job_status",
        lambda *a, **kw: True,
    )


def test_run_local_emits_telemetry_success(monkeypatch):
    """(a) run_local 정상 → telemetry `backtest.local.success` 증가."""
    _force_local_simulate_success(monkeypatch)

    res = backtest_service.run_local_backtest(
        preset="momentum",
        symbols=["005930", "000660"],
        market="KR",
        start_date="2024-01-01",
        end_date="2024-12-31",
        user_id=1,
    )
    assert res.get("status") == "completed"
    snap = tel.snapshot()
    assert snap["counters"].get("backtest.local.success", 0) >= 1


def test_run_local_emits_telemetry_fail_db_error(monkeypatch):
    """(b) save_backtest_job DB 에러 → telemetry `backtest.local.fail.db_error`."""
    from sqlalchemy.exc import OperationalError

    def fake_save(**kw):
        raise OperationalError("INSERT", {}, Exception("boom"))

    monkeypatch.setattr(
        backtest_service.strategy_store, "save_backtest_job", fake_save
    )
    monkeypatch.setattr(
        backtest_service.strategy_store, "update_job_status", lambda *a, **kw: True
    )

    from services.exceptions import ServiceError
    with pytest.raises(ServiceError):
        backtest_service.run_local_backtest(
            preset="momentum",
            symbols=["005930"],
            market="KR",
            start_date="2024-01-01",
            end_date="2024-12-31",
            user_id=1,
        )
    snap = tel.snapshot()
    fail_total = sum(
        v for k, v in snap["counters"].items()
        if k.startswith("backtest.local.fail.")
    )
    assert fail_total >= 1


def test_service_error_handler_includes_error_id():
    """(c) ServiceError 핸들러 응답 본문에 `error_id` 8자리 hex 포함.

    PostgreSQL 의존 없이 핸들러를 직접 호출하여 검증.
    """
    import asyncio
    import json
    from fastapi import Request
    from main import service_error_handler
    from services.exceptions import NotFoundError

    # 가짜 Request scope
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/backtest/result/non-existent-xxx",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 0),
    }
    req = Request(scope)
    exc = NotFoundError("백테스트 작업을 찾을 수 없습니다: non-existent-xxx")

    resp = asyncio.new_event_loop().run_until_complete(
        service_error_handler(req, exc)
    )
    body = json.loads(resp.body.decode())
    assert resp.status_code == 404
    assert "detail" in body
    assert "error_id" in body
    assert isinstance(body["error_id"], str)
    assert re.fullmatch(r"[0-9a-f]{8}", body["error_id"])

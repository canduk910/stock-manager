"""fire-and-poll 패턴 단위 테스트.

POST /run/preset → 즉시 {job_id, status:'running', mcp_job_id} 반환 (결과 대기 X).
GET /result/{job_id} (poll_backtest_job) → DB running 행 + mcp_job_id 로 MCP wait=False 1회 조회.
- MCP 진행 중 → DB 그대로(running)
- MCP 완료 → save_backtest_result + status=completed
- MCP 실패 → update_job_failed(error_message) + status=failed (친화 메시지 사용)
- mcp_job_id 부재 또는 KIS_MCP_ENABLED=False → DB 그대로 graceful

backtester EC2 실 데이터 없이 stock-manager 측 흐름만 검증.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from services import backtest_service
from services.exceptions import ExternalAPIError, NotFoundError


def _wrap_mcp(payload: dict) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


# ── _submit_mcp_job: MCP 1단계만 호출 ─────────────────────────────────


def test_submit_mcp_job_returns_id_no_wait():
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": {"job_id": "mcp-abc-1"}})

    out = backtest_service._submit_mcp_job(client, "run_preset_backtest_tool", {"strategy_id": "sma_crossover"})
    assert out == "mcp-abc-1"
    # get_backtest_result_tool 은 호출되지 않아야 한다 (fire-and-poll 핵심)
    called_tools = [c.args[0] for c in client.call_tool.call_args_list]
    assert "get_backtest_result_tool" not in called_tools


def test_submit_mcp_job_missing_job_id_raises():
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": {"unexpected": True}})
    with pytest.raises(ExternalAPIError, match="job_id"):
        backtest_service._submit_mcp_job(client, "run_preset_backtest_tool", {})


# ── _fetch_mcp_result_nowait: 진행 중/완료/실패 분기 ────────────────────


def test_fetch_result_running_returns_none():
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": {"status": "running"}})
    assert backtest_service._fetch_mcp_result_nowait(client, "mcp-1") is None


def test_fetch_result_in_progress_returns_none():
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": {"status": "in_progress"}})
    assert backtest_service._fetch_mcp_result_nowait(client, "mcp-2") is None


def test_fetch_result_completed_returns_data():
    client = MagicMock()
    payload = {"status": "completed", "result": {"metrics": {"basic": {"total_return": 12.3}}}}
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": payload})
    out = backtest_service._fetch_mcp_result_nowait(client, "mcp-3")
    assert out == payload


def test_fetch_result_failed_raises_external_api_error():
    """MCP success:false 응답은 _extract_mcp_content 단계에서 ExternalAPIError raise."""
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": False, "error": "데이터 준비 실패: 'vps'"})
    with pytest.raises(ExternalAPIError):
        backtest_service._fetch_mcp_result_nowait(client, "mcp-4")


# ── run_preset_backtest: 즉시 반환 (fire-and-poll) ─────────────────────


def test_run_preset_backtest_returns_running_immediately():
    """POST 진입점은 즉시 {status:'running', mcp_job_id} 반환 — get_backtest_result_tool 호출 안 함."""
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": {"job_id": "mcp-xyz-99"}})

    with patch.object(backtest_service, "get_mcp_client", return_value=client), \
         patch.object(backtest_service.strategy_store, "save_backtest_job", return_value={}) as save_job, \
         patch.object(backtest_service.strategy_store, "update_job_status", return_value=True) as set_status, \
         patch.object(backtest_service.strategy_store, "set_mcp_job_id", return_value=True) as set_mcp:

        out = backtest_service.run_preset_backtest(
            preset="sma_crossover",
            symbol="005930",
            market="KR",
            user_id=42,
        )

    # Write-Ahead 호출 검증
    save_job.assert_called_once()
    save_kwargs = save_job.call_args.kwargs
    assert save_kwargs["user_id"] == 42
    assert save_kwargs["strategy_name"] == "sma_crossover"
    assert save_kwargs["symbol"] == "005930"

    # status="running" 으로 즉시 갱신
    set_status.assert_called_once_with(out["job_id"], "running")
    # MCP job_id 영속
    set_mcp.assert_called_once_with(out["job_id"], "mcp-xyz-99")

    # 응답 형태 — 즉시 반환, result 키 없음
    assert out["status"] == "running"
    assert out["mcp_job_id"] == "mcp-xyz-99"
    assert "result" not in out

    # 결과 대기 호출 (get_backtest_result_tool) 발생 안 함
    called_tools = [c.args[0] for c in client.call_tool.call_args_list]
    assert called_tools == ["run_preset_backtest_tool"]


def test_run_preset_submit_failure_marks_failed_and_raises():
    """MCP 제출 단계 실패 시 DB 행 status=failed + error_message 기록 후 ExternalAPIError raise."""
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": False, "error": "전략 검증 실패: invalid"})

    with patch.object(backtest_service, "get_mcp_client", return_value=client), \
         patch.object(backtest_service.strategy_store, "save_backtest_job", return_value={}), \
         patch.object(backtest_service.strategy_store, "update_job_status"), \
         patch.object(backtest_service.strategy_store, "update_job_failed", return_value=True) as set_failed:
        with pytest.raises(ExternalAPIError, match="전략 검증 실패|MCP 백테스트 실패"):
            backtest_service.run_preset_backtest(
                preset="sma_crossover",
                symbol="005930",
                market="KR",
                user_id=1,
            )
    set_failed.assert_called_once()
    args = set_failed.call_args.args
    assert "전략 검증 실패" in args[1] or "MCP 백테스트 실패" in args[1]


# ── poll_backtest_job: lazy MCP 폴링 ─────────────────────────────────


def test_poll_returns_completed_job_without_mcp_call():
    """이미 completed 상태면 MCP 호출 없이 DB 행 반환."""
    completed_job = {"job_id": "j-1", "status": "completed", "mcp_job_id": "mcp-1", "result_json": {"x": 1}}
    with patch.object(backtest_service.strategy_store, "get_job", return_value=completed_job), \
         patch.object(backtest_service, "get_mcp_client") as mc:
        out = backtest_service.poll_backtest_job("j-1")
    assert out["status"] == "completed"
    mc.assert_not_called()


def test_poll_running_with_mcp_progress_keeps_running():
    """running 상태에서 MCP 진행 중이면 DB 행 그대로 반환(폴링 트리거만 발생)."""
    running_job = {"job_id": "j-2", "status": "running", "mcp_job_id": "mcp-2"}
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": {"status": "running"}})

    with patch.object(backtest_service, "KIS_MCP_ENABLED", True), \
         patch.object(backtest_service, "get_mcp_client", return_value=client), \
         patch.object(backtest_service.strategy_store, "get_job", return_value=running_job):
        out = backtest_service.poll_backtest_job("j-2", _user_id=1)

    assert out["status"] == "running"
    # MCP wait=False 호출이 정확히 1회 발생
    assert client.call_tool.call_count == 1
    args, kwargs = client.call_tool.call_args
    assert args[0] == "get_backtest_result_tool"
    assert args[1].get("wait") is False


def test_poll_running_with_mcp_completed_persists_metrics():
    """MCP 완료 응답 시 save_backtest_result 호출 + status=completed."""
    running_job = {"job_id": "j-3", "status": "running", "mcp_job_id": "mcp-3"}
    completed_job = {"job_id": "j-3", "status": "completed", "result_json": {"result": {"metrics": {"basic": {"total_return": 8.0}}}}}
    payload = {"status": "completed", "result": {"metrics": {"basic": {"total_return": 8.0, "annual_return": 2.0, "max_drawdown": -3.0}, "risk": {}, "trading": {}}}}
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": True, "data": payload})

    with patch.object(backtest_service, "KIS_MCP_ENABLED", True), \
         patch.object(backtest_service, "get_mcp_client", return_value=client), \
         patch.object(backtest_service.strategy_store, "get_job", side_effect=[running_job, completed_job]), \
         patch.object(backtest_service.strategy_store, "save_backtest_result", return_value=True) as save_res:
        out = backtest_service.poll_backtest_job("j-3", _user_id=1)

    save_res.assert_called_once()
    saved_kwargs = save_res.call_args.kwargs
    # _save_completed → save_backtest_result(job_id=..., metrics=..., result_json=..., completed_at=...)
    assert saved_kwargs["job_id"] == "j-3"
    assert saved_kwargs["metrics"]["total_return_pct"] == 8.0
    assert out["status"] == "completed"


def test_poll_running_with_mcp_failure_classifies_friendly_message():
    """MCP success:false 응답 시 친화 메시지로 update_job_failed."""
    running_job = {"job_id": "j-4", "status": "running", "mcp_job_id": "mcp-4"}
    failed_job = {"job_id": "j-4", "status": "failed", "result_json": {"error_message": "..."}}
    client = MagicMock()
    client.call_tool.return_value = _wrap_mcp({"success": False, "error": "데이터 준비 실패: 'vps'"})

    with patch.object(backtest_service, "KIS_MCP_ENABLED", True), \
         patch.object(backtest_service, "get_mcp_client", return_value=client), \
         patch.object(backtest_service.strategy_store, "get_job", side_effect=[running_job, failed_job]), \
         patch.object(backtest_service.strategy_store, "update_job_failed", return_value=True) as set_failed:
        out = backtest_service.poll_backtest_job("j-4", _user_id=1)

    set_failed.assert_called_once()
    args = set_failed.call_args.args
    err_msg = args[1]
    assert "백테스트 인증 설정 오류" in err_msg or "kis_devlp.yaml" in err_msg
    assert out["status"] == "failed"


def test_poll_missing_job_raises_not_found():
    with patch.object(backtest_service.strategy_store, "get_job", return_value=None):
        with pytest.raises(NotFoundError):
            backtest_service.poll_backtest_job("missing")


def test_poll_running_no_mcp_job_id_returns_db_row():
    """alembic 미적용 환경 — mcp_job_id 부재면 MCP 호출 안 하고 DB 행 그대로 반환(graceful)."""
    running_job = {"job_id": "j-5", "status": "running", "mcp_job_id": None}
    with patch.object(backtest_service.strategy_store, "get_job", return_value=running_job), \
         patch.object(backtest_service, "get_mcp_client") as mc:
        out = backtest_service.poll_backtest_job("j-5", _user_id=1)
    assert out["status"] == "running"
    mc.assert_not_called()


def test_poll_running_mcp_disabled_returns_db_row():
    running_job = {"job_id": "j-6", "status": "running", "mcp_job_id": "mcp-6"}
    with patch.object(backtest_service, "KIS_MCP_ENABLED", False), \
         patch.object(backtest_service.strategy_store, "get_job", return_value=running_job), \
         patch.object(backtest_service, "get_mcp_client") as mc:
        out = backtest_service.poll_backtest_job("j-6", _user_id=1)
    assert out["status"] == "running"
    mc.assert_not_called()


def test_poll_mcp_transient_error_keeps_running():
    """MCP 폴링이 일시적 네트워크 오류 등으로 실패해도 status는 running 유지(다음 폴링 재시도)."""
    running_job = {"job_id": "j-7", "status": "running", "mcp_job_id": "mcp-7"}
    client = MagicMock()
    client.call_tool.side_effect = ConnectionError("temp network")

    with patch.object(backtest_service, "KIS_MCP_ENABLED", True), \
         patch.object(backtest_service, "get_mcp_client", return_value=client), \
         patch.object(backtest_service.strategy_store, "get_job", return_value=running_job), \
         patch.object(backtest_service.strategy_store, "update_job_failed") as set_failed:
        out = backtest_service.poll_backtest_job("j-7", _user_id=1)

    # 일시 오류는 failed 마킹하지 않음 (다음 폴링에서 재시도)
    set_failed.assert_not_called()
    assert out["status"] == "running"


# ── get_backtest_result 위임 검증 ──────────────────────────────────


def test_failed_job_surfaces_error_message_for_frontend():
    """프론트 useBacktest 가 res.error 를 직접 사용하므로 result_json.error_message 를 top-level 로 expose."""
    failed_job = {
        "job_id": "j-9",
        "status": "failed",
        "result_json": {"error_message": "백테스트 인증 설정 오류: kis_devlp.yaml ..."},
    }
    with patch.object(backtest_service.strategy_store, "get_job", return_value=failed_job):
        out = backtest_service.poll_backtest_job("j-9")
    assert out["status"] == "failed"
    assert out["error"] == "백테스트 인증 설정 오류: kis_devlp.yaml ..."


def test_get_backtest_result_delegates_to_poll():
    job = {"job_id": "j-8", "status": "completed", "mcp_job_id": "mcp-8"}
    with patch.object(backtest_service.strategy_store, "get_job", return_value=job):
        out = backtest_service.get_backtest_result("j-8")
    assert out["status"] == "completed"
    assert out["job_id"] == "j-8"

"""AI자문 fire-and-poll 작업 관리 (in-memory).

2026-05-09: refresh_stock_data / generate_ai_report 가 30초~10분 소요되어
nginx /api/ 90s 타임아웃 또는 클라이언트 timeout으로 HTTP 504 발생하는 결함.
504 후에도 백엔드 작업은 계속 진행되는데, 사용자는 결과 회수가 불가해
재호출(중복 실행) 유발.

해결: fire-and-poll 패턴 (백테스트 services/backtest_service 동일).
- POST /refresh?async=true → submit_job() → 즉시 {job_id, status:"running"}
- POST /analyze?async=true → 동일
- GET /jobs/{job_id} → poll_job() (running/completed/failed + result/error)

In-memory dict 사용 (EC2 단일 인스턴스 가정. 멀티 인스턴스 확장 시 Redis 권장).
threading.Thread로 백그라운드 실행 (FastAPI sync endpoint 호환).
완료된 job은 1시간 후 자동 정리 (메모리 보호).
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional

from services.exceptions import NotFoundError, ServiceError

logger = logging.getLogger(__name__)


# ── 작업 저장소 ──────────────────────────────────────────────────────────

_KST = timezone(timedelta(hours=9))


def _now_iso() -> str:
    return datetime.now(_KST).isoformat()


# job_id → job dict
# job dict: {
#   id, kind('refresh'|'analyze'), code, market, user_id,
#   status('running'|'completed'|'failed'),
#   started_at, completed_at, result, error_message,
# }
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()

# 완료된 job 보존 시간 (메모리 보호)
_RETENTION_SECONDS = 3600  # 1시간


def _cleanup_old_jobs() -> None:
    """완료/실패한 1시간 초과 job 제거 (호출 시점 lazy 정리)."""
    cutoff = datetime.now(_KST) - timedelta(seconds=_RETENTION_SECONDS)
    cutoff_iso = cutoff.isoformat()
    with _jobs_lock:
        to_delete = [
            jid for jid, j in _jobs.items()
            if j.get("status") in ("completed", "failed")
            and (j.get("completed_at") or "") < cutoff_iso
        ]
        for jid in to_delete:
            _jobs.pop(jid, None)


def _new_job_id() -> str:
    return uuid.uuid4().hex[:12]


# ── 작업 제출/조회 ───────────────────────────────────────────────────────


def submit_job(
    kind: str,
    code: str,
    market: str,
    user_id: int,
    func: Callable[..., Any],
    /,
    *args,
    **kwargs,
) -> dict:
    """백그라운드 작업 제출. 즉시 job dict 반환.

    Args:
        kind/code/market/user_id/func: positional-only (`/` 이전).
                                       호출자가 user_id를 keyword로 func에 전달해도
                                       submit_job 자체 시그니처와 충돌 없음.
        *args, **kwargs: func에 그대로 전달 (kwargs에 user_id 있어도 OK)

    Returns:
        {job_id, kind, code, market, status:"running", started_at, ...}

    Note:
        2026-05-10 결함 — `/` 없을 때 호출자의 user_id keyword가 submit_job의
        positional user_id와 충돌해 TypeError → HTTP 500. positional-only로
        분리해 충돌 차단.
    """
    if kind not in ("refresh", "analyze"):
        raise ServiceError(f"알 수 없는 작업 유형: {kind}")

    _cleanup_old_jobs()

    job_id = _new_job_id()
    job = {
        "id": job_id,
        "kind": kind,
        "code": code,
        "market": market,
        "user_id": user_id,
        "status": "running",
        "started_at": _now_iso(),
        "completed_at": None,
        "result": None,
        "error_message": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job

    def _worker():
        try:
            result = func(*args, **kwargs)
            with _jobs_lock:
                cur = _jobs.get(job_id)
                if cur is None:
                    return
                cur["status"] = "completed"
                cur["completed_at"] = _now_iso()
                cur["result"] = result
            logger.info(
                "[advisory_jobs] job %s (%s %s/%s) completed",
                job_id, kind, market, code,
            )
        except Exception as e:
            with _jobs_lock:
                cur = _jobs.get(job_id)
                if cur is None:
                    return
                cur["status"] = "failed"
                cur["completed_at"] = _now_iso()
                cur["error_message"] = str(e)
            logger.warning(
                "[advisory_jobs] job %s (%s %s/%s) failed: %s",
                job_id, kind, market, code, e,
            )

    t = threading.Thread(target=_worker, daemon=True, name=f"advisory-{kind}-{job_id}")
    t.start()

    # 응답에는 result/error는 빠짐 (running 상태)
    return {
        "job_id": job_id,
        "kind": kind,
        "code": code,
        "market": market,
        "status": "running",
        "started_at": job["started_at"],
        "message": (
            "데이터 수집 중입니다. 완료까지 30초~3분 소요됩니다."
            if kind == "refresh"
            else "AI 자문 보고서 생성 중입니다. 완료까지 1~3분 소요됩니다."
        ),
    }


def poll_job(job_id: str, user_id: Optional[int] = None) -> dict:
    """작업 상태 + (완료 시) 결과 조회.

    Args:
        job_id: 작업 ID
        user_id: 권한 검증 (None 이면 검증 안 함)

    Returns:
        running: {job_id, status:"running", started_at, message}
        completed: {job_id, status:"completed", started_at, completed_at, result}
        failed: {job_id, status:"failed", started_at, completed_at, error_message}

    Raises:
        NotFoundError: job_id 없음 (만료 1시간 경과 또는 잘못된 ID)
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise NotFoundError(
                f"작업을 찾을 수 없습니다: {job_id} (만료되었거나 잘못된 ID)"
            )

        # user_id 권한 검증 (자기 작업만 조회 가능)
        if user_id is not None and job.get("user_id") != user_id:
            raise NotFoundError(f"작업을 찾을 수 없습니다: {job_id}")

        # 완료/실패 시 result/error 포함, running 시 안내 메시지
        result = {
            "job_id": job["id"],
            "kind": job["kind"],
            "code": job["code"],
            "market": job["market"],
            "status": job["status"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
        }
        if job["status"] == "completed":
            result["result"] = job["result"]
        elif job["status"] == "failed":
            result["error_message"] = job["error_message"]
        else:  # running
            elapsed = _elapsed_seconds(job["started_at"])
            result["elapsed_seconds"] = elapsed
            result["message"] = (
                f"데이터 수집 중... ({elapsed}초 경과)"
                if job["kind"] == "refresh"
                else f"AI 보고서 생성 중... ({elapsed}초 경과)"
            )
        return result


def _elapsed_seconds(started_at_iso: str) -> int:
    try:
        started = datetime.fromisoformat(started_at_iso)
        return int((datetime.now(_KST) - started).total_seconds())
    except Exception:
        return 0


def get_job_count() -> dict:
    """현재 in-memory job 개수 (운영 진단용)."""
    with _jobs_lock:
        running = sum(1 for j in _jobs.values() if j.get("status") == "running")
        completed = sum(1 for j in _jobs.values() if j.get("status") == "completed")
        failed = sum(1 for j in _jobs.values() if j.get("status") == "failed")
    return {"total": len(_jobs), "running": running, "completed": completed, "failed": failed}


def _reset_for_tests() -> None:
    """테스트 전용 — _jobs dict 초기화."""
    with _jobs_lock:
        _jobs.clear()

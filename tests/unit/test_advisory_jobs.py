"""advisory_jobs (fire-and-poll) 회귀 테스트.

2026-05-09: refresh_stock_data / generate_ai_report 가 30초~3분 소요되어
nginx /api/ 90s 타임아웃 또는 클라이언트 timeout으로 HTTP 504 발생 + 백엔드는
계속 실행되는데 사용자가 결과 회수 불가해 재호출(중복 실행) 유발하던 결함.
"""

import time

import pytest

from services import advisory_jobs
from services.exceptions import NotFoundError, ServiceError


@pytest.fixture(autouse=True)
def _reset_jobs():
    advisory_jobs._reset_for_tests()
    yield
    advisory_jobs._reset_for_tests()


# ── submit_job ───────────────────────────────────────────────────────

def test_submit_job_returns_immediately_with_running_status():
    """fire-and-poll 핵심: 함수 실행 완료 전에 즉시 job_id + running 반환."""
    def slow_func():
        time.sleep(2)
        return {"data": "ok"}

    t0 = time.time()
    job = advisory_jobs.submit_job(
        "refresh", "005930", "KR", 1, slow_func,
    )
    elapsed = time.time() - t0

    assert elapsed < 0.5  # 함수 2초 sleep인데 0.5s 안에 반환
    assert job["status"] == "running"
    assert job["job_id"]
    assert job["kind"] == "refresh"
    assert job["code"] == "005930"
    assert "message" in job  # 사용자 안내 메시지
    assert "수집 중" in job["message"]


def test_submit_analyze_job_message_distinguishes_kind():
    """analyze는 다른 안내 메시지."""
    job = advisory_jobs.submit_job(
        "analyze", "005930", "KR", 1, lambda: {},
    )
    assert "보고서 생성 중" in job["message"]


def test_submit_invalid_kind_raises():
    """알 수 없는 kind → ServiceError."""
    with pytest.raises(ServiceError):
        advisory_jobs.submit_job("unknown", "005930", "KR", 1, lambda: {})


# ── poll_job ─────────────────────────────────────────────────────────

def test_poll_running_job_returns_status_with_elapsed():
    """running 상태는 elapsed_seconds + 진행 메시지 포함."""
    def slow():
        time.sleep(2)
        return {"data": "x"}

    job = advisory_jobs.submit_job("refresh", "005930", "KR", 1, slow)
    poll = advisory_jobs.poll_job(job["job_id"], user_id=1)
    assert poll["status"] == "running"
    assert "elapsed_seconds" in poll
    assert poll["elapsed_seconds"] >= 0


def test_poll_completed_job_returns_result():
    """완료 후 polling은 result 포함."""
    def fast():
        return {"data": "complete"}

    job = advisory_jobs.submit_job("refresh", "005930", "KR", 1, fast)
    # 백그라운드 thread 완료 대기 (최대 1초)
    for _ in range(20):
        time.sleep(0.05)
        poll = advisory_jobs.poll_job(job["job_id"], user_id=1)
        if poll["status"] == "completed":
            break
    assert poll["status"] == "completed"
    assert poll["result"] == {"data": "complete"}
    assert poll["completed_at"] is not None


def test_poll_failed_job_returns_error_message():
    """함수 raise 시 status=failed + error_message 포함 + 결과 회수 안 됨."""
    def boom():
        raise RuntimeError("boom!")

    job = advisory_jobs.submit_job("refresh", "005930", "KR", 1, boom)
    for _ in range(20):
        time.sleep(0.05)
        poll = advisory_jobs.poll_job(job["job_id"], user_id=1)
        if poll["status"] == "failed":
            break
    assert poll["status"] == "failed"
    assert "boom" in poll["error_message"]


def test_poll_unknown_job_id_raises_not_found():
    """잘못된 job_id 또는 만료 → NotFoundError(404)."""
    with pytest.raises(NotFoundError):
        advisory_jobs.poll_job("does-not-exist", user_id=1)


def test_poll_other_users_job_raises_not_found():
    """user_id 권한 검증 — 타 사용자 job 조회 차단."""
    job = advisory_jobs.submit_job("refresh", "005930", "KR", 99, lambda: {})
    with pytest.raises(NotFoundError):
        advisory_jobs.poll_job(job["job_id"], user_id=1)


def test_poll_without_user_id_skips_permission_check():
    """user_id=None 호출은 권한 검사 건너뜀 (운영 진단용)."""
    job = advisory_jobs.submit_job("refresh", "005930", "KR", 99, lambda: {})
    poll = advisory_jobs.poll_job(job["job_id"], user_id=None)
    assert poll["job_id"] == job["job_id"]


# ── 동시성 ──────────────────────────────────────────────────────────

def test_concurrent_submit_returns_unique_job_ids():
    """동시 submit 시 job_id 충돌 없음."""
    jobs = [
        advisory_jobs.submit_job("refresh", f"00593{i}", "KR", 1, lambda: {})
        for i in range(20)
    ]
    ids = [j["job_id"] for j in jobs]
    assert len(set(ids)) == 20


def test_get_job_count_reports_status_breakdown():
    """get_job_count 운영 진단용 — running/completed/failed 집계."""
    advisory_jobs.submit_job("refresh", "005930", "KR", 1, lambda: {"x": 1})
    time.sleep(0.2)  # 완료 대기
    count = advisory_jobs.get_job_count()
    assert count["total"] >= 1
    assert "running" in count
    assert "completed" in count
    assert "failed" in count


# ── positional-only 시그니처 회귀 (2026-05-10 결함) ────────────

def test_submit_job_accepts_user_id_kwarg_for_func():
    """호출자가 user_id를 keyword로 func에 전달해도 submit_job 자체 시그니처와
    충돌 없음 (positional-only `/` 분리 가드).

    routers/advisory.py 의 실제 호출 패턴:
        submit_job("analyze", code, market, user["id"], gen_func,
                   code, market, name, user_id=user["id"], user_comment=...)

    이전 결함(2026-05-10): user_id keyword가 submit_job positional user_id와
    충돌해 TypeError → HTTP 500.
    """
    captured = {}

    def fake_func(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return {"ok": True}

    job = advisory_jobs.submit_job(
        "analyze", "005830", "KR", 1,    # positional 5개 (job 메타)
        fake_func,
        "005830", "KR", "DB손해보험",      # *args (func 에 전달)
        user_id=1, user_comment="가설",   # **kwargs (func 에 전달, user_id 키워드 허용)
    )
    assert job["status"] == "running"
    # 백그라운드 thread 완료 대기
    for _ in range(20):
        time.sleep(0.05)
        poll = advisory_jobs.poll_job(job["job_id"], user_id=1)
        if poll["status"] == "completed":
            break
    assert poll["status"] == "completed"
    # func 호출이 정상적으로 args/kwargs를 받음
    assert captured["args"] == ("005830", "KR", "DB손해보험")
    assert captured["kwargs"] == {"user_id": 1, "user_comment": "가설"}

"""트랙 3: prewarm_macro_summary + APScheduler 등록 검증."""
from unittest.mock import patch

from services import macro_service


def test_prewarm_calls_all_sections():
    """prewarm_macro_summary는 indices/sentiment/summary 세 섹션을 모두 호출."""
    with patch.object(macro_service, "get_indices", return_value={"indices": []}) as m_idx, \
         patch.object(macro_service, "get_sentiment", return_value={"vix": 20}) as m_sent, \
         patch.object(macro_service, "get_summary", return_value={"indices": None}) as m_sum:

        result = macro_service.prewarm_macro_summary()

        assert m_idx.called
        assert m_sent.called
        assert m_sum.called

    assert "prewarmed" in result
    assert "errors" in result
    assert set(result["prewarmed"]) >= {"indices", "sentiment", "summary"}
    assert result["errors"] == []


def test_prewarm_partial_failure_continues():
    """한 섹션 실패해도 나머지 계속."""
    with patch.object(macro_service, "get_indices", side_effect=RuntimeError("fail-idx")), \
         patch.object(macro_service, "get_sentiment", return_value={"vix": 20}), \
         patch.object(macro_service, "get_summary", return_value={}):

        result = macro_service.prewarm_macro_summary()

    assert "summary" in result["prewarmed"]
    assert "sentiment" in result["prewarmed"]
    assert any("indices" in e for e in result["errors"])


def test_scheduler_registers_macro_prewarm():
    """setup_scheduler 호출 시 macro_prewarm job 등록 확인. apscheduler 없으면 skip."""
    import pytest

    try:
        from apscheduler.schedulers.background import BackgroundScheduler  # noqa: F401
    except ImportError:
        pytest.skip("apscheduler not installed (local dev). Skipping scheduler smoke test.")

    from services import scheduler_service

    # 기존 스케줄러 정리
    scheduler_service.shutdown_scheduler()

    scheduler_service.setup_scheduler()
    try:
        status = scheduler_service.get_scheduler_status()
        assert status["running"] is True
        job_ids = {j["id"] for j in status["jobs"]}
        assert "macro_prewarm" in job_ids, f"macro_prewarm not registered. jobs={job_ids}"
    finally:
        scheduler_service.shutdown_scheduler()

"""투자 파이프라인 스케줄러.

APScheduler로 08:00(KR) / 16:00(US) 자동 실행.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

_scheduler = None


def _run_pipeline_job(market: str):
    """스케줄러에서 호출되는 잡 함수."""
    from services.pipeline_service import run_pipeline
    try:
        result = run_pipeline(market)
        logger.info(f"[스케줄러] {market} 파이프라인 완료: 보고서 #{result['report_id']}, 추천 {result['recommended_count']}건")
    except Exception as e:
        logger.error(f"[스케줄러] {market} 파이프라인 실패: {e}", exc_info=True)


def setup_scheduler():
    """APScheduler 시작 (08:00 KR / 16:00 US KST)."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        _scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        _scheduler.add_job(
            _run_pipeline_job,
            CronTrigger(hour=8, minute=0),
            args=["KR"],
            id="pipeline_kr",
            name="KR 투자 파이프라인 (08:00)",
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_pipeline_job,
            CronTrigger(hour=16, minute=0),
            args=["US"],
            id="pipeline_us",
            name="US 투자 파이프라인 (16:00)",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("[스케줄러] 투자 파이프라인 스케줄러 시작 (08:00 KR / 16:00 US)")
    except ImportError:
        logger.warning("[스케줄러] apscheduler 미설치 — 스케줄러 비활성화")
    except Exception as e:
        logger.error(f"[스케줄러] 시작 실패: {e}")


def shutdown_scheduler():
    """스케줄러 종료."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("[스케줄러] 투자 파이프라인 스케줄러 종료")
        _scheduler = None


def get_scheduler_status() -> dict:
    """스케줄러 상태 조회."""
    if not _scheduler or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        next_run = job.next_run_time
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
        })
    return {"running": True, "jobs": jobs}

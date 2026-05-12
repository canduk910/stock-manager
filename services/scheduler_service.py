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


def _run_macro_cleanup_job():
    """일일 자정 매크로 GPT 캐시 cleanup (2026-05-09 신규).

    KST 00:05 매일 실행. macro_gpt_cache 테이블에서 오늘 이전 모든 row 삭제 →
    매크로 정보는 당일치만 유지. cache.db 의 macro:* TTL 캐시는 미터치.
    """
    from stock import macro_store
    try:
        deleted = macro_store.delete_before_today()
        logger.info(f"[스케줄러] 매크로 캐시 cleanup 완료: {deleted}건 삭제")
    except Exception as e:
        logger.error(f"[스케줄러] 매크로 캐시 cleanup 실패: {e}", exc_info=True)


def _run_macro_prewarm_job():
    """일일 매크로 pre-warm (2026-05-12 신규, MacroSentinel 도메인 자문 결과 KST 00:05 채택).

    cleanup 직후 indices/sentiment/summary 캐시를 미리 적재 →
    매크로 페이지 자정 후 첫 사용자 응답 시간 GPT 15~30s → < 1s.
    부분 실패는 logger.warning로만 기록, 함수 자체는 raise 안 함.
    """
    from services.macro_service import prewarm_macro_summary
    try:
        result = prewarm_macro_summary()
        ok = len(result.get("prewarmed", []))
        err = len(result.get("errors", []))
        logger.info(f"[스케줄러] 매크로 pre-warm 완료: {ok}개 적재, {err}건 오류")
    except Exception as e:
        logger.error(f"[스케줄러] 매크로 pre-warm 실패: {e}", exc_info=True)


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
        # 2026-05-09: 매크로 GPT 캐시 일일 cleanup (KST 00:05).
        # 자정 직후 5분 여유로 자정 경계 race 방지(00:00 정각 호출은 일부 환경에서 누락).
        _scheduler.add_job(
            _run_macro_cleanup_job,
            CronTrigger(hour=0, minute=5),
            id="macro_cleanup",
            name="매크로 GPT 캐시 cleanup (00:05)",
            replace_existing=True,
        )
        # 2026-05-12: 매크로 pre-warm (KST 00:05, cleanup 직후).
        # MacroSentinel 도메인 자문: 한국 거주자 새벽 사용자 즉시 응답이 주 목적.
        # 미국 마감 후 정확도 향상은 후속 작업(06:30 보조 cron) 후 검토.
        _scheduler.add_job(
            _run_macro_prewarm_job,
            CronTrigger(hour=0, minute=5),
            id="macro_prewarm",
            name="매크로 pre-warm (00:05)",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info("[스케줄러] 스케줄러 시작 (08:00 KR / 16:00 US / 00:05 cleanup+prewarm)")
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

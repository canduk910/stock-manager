"""투자 파이프라인 스케줄러.

APScheduler로 08:00(KR) / 16:00(US) 자동 실행.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

from db.utils import KST

_scheduler = None

# REQ-FH-EXT-CRON-01: 외국인 보유 백필 cron 활성 종목 cap (MVP 부하 가시화)
_FH_BACKFILL_CAP = 50

# REQ-FH-EXT-CRON-01: 종목 호출 간 sleep (KIS 초당 2회 안정선)
_FH_BACKFILL_SLEEP_SEC = 0.5


def _now_kst() -> datetime:
    """현재 KST 시각. 테스트에서 monkeypatch 가능."""
    return datetime.now(KST)


def _all_advisory_users_codes() -> list[tuple[str, str]]:
    """모든 사용자 advisory_stocks에서 (code, market) 추출. dedup 적용.

    REQ-FH-EXT-CRON-01: 활성 종목 = advisory_stocks 전체 + watchlist 국내 (50 cap).
    """
    seen: set[tuple[str, str]] = set()
    try:
        from db.session import get_session
        from db.models.advisory import AdvisoryStock
        with get_session() as db:
            rows = db.query(AdvisoryStock.code, AdvisoryStock.market).distinct().all()
            for r in rows:
                key = (r[0], (r[1] or "KR").upper())
                seen.add(key)
    except Exception as exc:
        logger.warning(f"[스케줄러] advisory_stocks 조회 실패: {exc}")
    return list(seen)


def _all_watchlist_codes() -> list[tuple[str, str]]:
    """모든 사용자 watchlist에서 (code, market) 추출. dedup 적용."""
    seen: set[tuple[str, str]] = set()
    try:
        from db.session import get_session
        from db.models.watchlist import Watchlist
        with get_session() as db:
            rows = db.query(Watchlist.code, Watchlist.market).distinct().all()
            for r in rows:
                key = (r[0], (r[1] or "KR").upper())
                seen.add(key)
    except Exception as exc:
        logger.warning(f"[스케줄러] watchlist 조회 실패: {exc}")
    return list(seen)


def _run_foreign_holding_backfill_job():
    """REQ-FH-EXT-CRON-01: 외국인 보유 일별 백필 (KST 18:00).

    활성 국내 종목 (advisory_stocks ∪ watchlist KR) 외국인 보유 데이터를
    `fetch_foreign_holding(code, days=30)` 호출로 누적 캐시에 저장.

    안전 정책 (OrderAdvisor 자문):
    - 토/일 weekday() ≥ 5 → 즉시 return + KIS 호출 0회
    - 50개 cap (단계적 부하 가시화)
    - 종목간 sleep 0.5s (KIS 초당 2회 안정선)
    - 종목별 try/except (1개 실패해도 다음 종목 진행, raise 금지)
    """
    started_at = time.time()
    try:
        now = _now_kst()
    except Exception:
        now = datetime.now(KST)

    if now.weekday() >= 5:  # 토(5)/일(6)
        logger.info(f"[스케줄러] 외국인 보유 백필 주말 skip (weekday={now.weekday()})")
        return

    try:
        from stock.utils import is_domestic
    except Exception as exc:
        logger.error(f"[스케줄러] is_domestic import 실패: {exc}")
        return

    # 활성 종목 수집 (advisory ∪ watchlist, KR만)
    try:
        adv = _all_advisory_users_codes() or []
        wat = _all_watchlist_codes() or []
    except Exception as exc:
        logger.error(f"[스케줄러] 활성 종목 조회 실패: {exc}")
        return

    seen: set[str] = set()
    candidates: list[str] = []
    for code, market in list(adv) + list(wat):
        if not code or (market or "KR").upper() != "KR":
            continue
        if not is_domestic(code):
            continue
        if code in seen:
            continue
        seen.add(code)
        candidates.append(code)

    if not candidates:
        logger.info("[스케줄러] 외국인 보유 백필 활성 종목 없음")
        return

    # 50개 cap
    if len(candidates) > _FH_BACKFILL_CAP:
        logger.warning(
            f"[스케줄러] 외국인 보유 백필 cap 적용: "
            f"{len(candidates)}개 → {_FH_BACKFILL_CAP}개로 truncate"
        )
        candidates = candidates[:_FH_BACKFILL_CAP]

    success = 0
    fail = 0
    from services import supply_demand_service  # 지연 import (circular 방지)
    for code in candidates:
        try:
            supply_demand_service.fetch_foreign_holding(code, days=30)
            success += 1
        except Exception as exc:
            fail += 1
            logger.warning(f"[스케줄러] 외국인 보유 백필 실패: {code} — {exc}")
        time.sleep(_FH_BACKFILL_SLEEP_SEC)

    elapsed = time.time() - started_at
    logger.info(
        f"[스케줄러] 외국인 보유 백필 완료: 성공 {success}건, 실패 {fail}건, "
        f"소요 {elapsed:.1f}초"
    )


def _run_semi_collector_job(collector_name: str):
    """반도체 수집기 단일 실행 (스케줄러).

    수집기 자체 try/except + service 레이어 try/except 2중 격리.
    raise 금지(잡 중단 방지).
    """
    try:
        from services import semiconductor_service
        out = semiconductor_service.run_collector(collector_name)
        logger.info(f"[스케줄러] 반도체 {collector_name} 수집 완료: {out}")
    except Exception as exc:
        logger.error(f"[스케줄러] 반도체 {collector_name} 수집 실패: {exc}", exc_info=True)


def _run_semi_evaluate_job():
    """매시 정각 시그널 평가 + 상태 변경 신호 발사."""
    try:
        from services import semiconductor_service
        out = semiconductor_service.evaluate_and_persist()
        n = len(out.get("signals_inserted", []))
        if n:
            logger.info(f"[스케줄러] 반도체 평가: 신호 {n}건 발사")
        else:
            logger.debug("[스케줄러] 반도체 평가: 신호 변경 없음")
    except Exception as exc:
        logger.error(f"[스케줄러] 반도체 평가 실패: {exc}", exc_info=True)


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


def _run_macro_factor_model_job():
    """거시 팩터(롤링 PCA) 모델 일배치 (KST 00:20, 2026-06-20 신규).

    cleanup(00:05)+prewarm(00:05) 이후 실행 → 충돌 없음(cleanup은 '오늘 이전'
    삭제, 당일 00:20 생성분 보존). 거시 10지표 7년 수집 → 롤링 PCA → 종목 베타
    → macro_store.save_today("factor_model"). 무거운 계산은 이 배치에서만.
    부분 실패는 build 내부 errors에 격리, 함수 자체는 raise 안 함(다른 잡 보호).
    """
    from services.macro_factor_model import build_and_cache_factor_model
    try:
        result = build_and_cache_factor_model()
        meta = result.get("meta", {})
        logger.info(
            "[스케줄러] 거시 팩터 모델 배치 완료: 윈도우 %s개, 종목 %s개, 오류 %s건",
            meta.get("n_windows"), meta.get("n_stocks"), len(result.get("errors", [])),
        )
    except Exception as e:
        logger.error(f"[스케줄러] 거시 팩터 모델 배치 실패: {e}", exc_info=True)


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


def _run_one_retention_table(label: str, delete_fn):
    """DB retention 잡의 테이블 1개 처리 단위 (2026-07-19 보강).

    dev-lead 지시 반영: 테이블별로 **독립된 `get_session()` 블록**을 열어
    "한 테이블 실패가 다른 테이블 삭제에 영향 없음" 불변식을 구조적으로 보장한다.
    - 세션 오픈~commit(또는 실패 시 rollback)이 테이블 단위로 완결되므로,
      한 테이블에서 DB 레벨 에러(FK 위반, 락 타임아웃 등)로 세션이 invalid 상태가 되어도
      이미 커밋된 이전 테이블의 삭제는 되돌아가지 않고, 다음 테이블은 새 세션이라 영향받지 않는다.
    - `get_session()` 컨텍스트 매니저가 예외 시 자체적으로 rollback+close 하므로
      별도 `db.rollback()` 호출은 불필요(중복 rollback 방지 위해 생략).
    - 일일 1회 배치이므로 세션 9회 오픈 비용은 무시 가능(성능 무관).

    delete_fn: `lambda db: Repository(db).delete_x_before(cutoff)` 형태의 콜러블.
    실패 시 예외를 삼키고 logger.error만 기록(잡 자체는 raise 안 함 — 스케줄러 보호).
    """
    from db.session import get_session

    try:
        with get_session() as db:
            deleted = delete_fn(db)
        logger.info(f"[스케줄러] DB retention: {label} {deleted}건 삭제")
    except Exception as e:
        logger.error(f"[스케줄러] DB retention: {label} 삭제 실패: {e}", exc_info=True)


def _run_db_retention_cleanup_job():
    """일일 DB retention cleanup (KST 03:00, 2026-07-17 신규 / 2026-07-19 세션 격리 보강).

    append-only 로그/이력 테이블 9종 정리 — RDS 스토리지 비용 절감.
    각 테이블을 **독립 `get_session()` 블록 + 독립 try/except**로 처리 —
    한 테이블의 DB 레벨 실패(세션 invalid화 포함)가 나머지 테이블 삭제를 막지 않는다.
    삭제 건수 logger.info, 실패 시 logger.error(잡 자체는 raise 안 함 — 스케줄러 보호).
    cutoff는 config.DB_RETENTION_* 값을 함수 실행 시점에 읽어 계산한다(import-time 캐시 금지).
    정리 제외: macro_regime_history / orders / reservations / tax_* / backtest_jobs /
    market_board_* / advisory_cache.
    """
    import config
    from datetime import timedelta
    from db.utils import now_kst

    from db.repositories.page_view_repo import PageViewRepository
    from db.repositories.admin_repo import AdminRepository
    from db.repositories.report_repo import ReportRepository
    from db.repositories.advisory_repo import AdvisoryRepository
    from db.repositories.semiconductor_repo import SemiconductorRepository

    def _cutoff(days: int) -> str:
        return (now_kst() - timedelta(days=days)).isoformat()

    # page_views
    cutoff = _cutoff(config.DB_RETENTION_PAGE_VIEWS_DAYS)
    _run_one_retention_table(
        f"page_views (< {cutoff})",
        lambda db: PageViewRepository(db).delete_before(cutoff),
    )

    # ai_usage_log
    cutoff = _cutoff(config.DB_RETENTION_AI_USAGE_DAYS)
    _run_one_retention_table(
        f"ai_usage_log (< {cutoff})",
        lambda db: AdminRepository(db).delete_ai_usage_before(cutoff),
    )

    # audit_log
    cutoff = _cutoff(config.DB_RETENTION_AUDIT_DAYS)
    _run_one_retention_table(
        f"audit_log (< {cutoff})",
        lambda db: AdminRepository(db).delete_audit_before(cutoff),
    )

    # recommendation_history
    cutoff = _cutoff(config.DB_RETENTION_RECOMMENDATION_DAYS)
    _run_one_retention_table(
        f"recommendation_history (< {cutoff})",
        lambda db: ReportRepository(db).delete_recommendations_before(cutoff),
    )

    # daily_reports (market별 최신 1건 보존)
    cutoff = _cutoff(config.DB_RETENTION_DAILY_REPORTS_DAYS)
    _run_one_retention_table(
        f"daily_reports (< {cutoff})",
        lambda db: ReportRepository(db).delete_daily_reports_before(cutoff),
    )

    # advisory_reports ((code,market)별 최신 1건 보존, advisory_cache 미터치)
    cutoff = _cutoff(config.DB_RETENTION_ADVISORY_REPORTS_DAYS)
    _run_one_retention_table(
        f"advisory_reports (< {cutoff})",
        lambda db: AdvisoryRepository(db).delete_reports_before(cutoff),
    )

    # portfolio_reports (user_id별 최신 1건 보존)
    cutoff = _cutoff(config.DB_RETENTION_PORTFOLIO_REPORTS_DAYS)
    _run_one_retention_table(
        f"portfolio_reports (< {cutoff})",
        lambda db: AdvisoryRepository(db).delete_portfolio_reports_before(cutoff),
    )

    # semi_signals
    cutoff = _cutoff(config.DB_RETENTION_SEMI_SIGNALS_DAYS)
    _run_one_retention_table(
        f"semi_signals (< {cutoff})",
        lambda db: SemiconductorRepository(db).delete_signals_before(cutoff),
    )

    # semi_indicator_values
    cutoff = _cutoff(config.DB_RETENTION_SEMI_INDICATORS_DAYS)
    _run_one_retention_table(
        f"semi_indicator_values (< {cutoff})",
        lambda db: SemiconductorRepository(db).delete_indicator_values_before(cutoff),
    )


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
        # 2026-06-20: 거시 팩터(롤링 PCA) 모델 일배치 (KST 00:20).
        # cleanup+prewarm(00:05) 이후 → 당일 00:20 생성분은 cleanup('오늘 이전' 삭제)
        # 대상 아님. 무거운 PCA는 이 배치에서만(요청 경로 read-only).
        _scheduler.add_job(
            _run_macro_factor_model_job,
            CronTrigger(hour=0, minute=20),
            id="macro_factor_model",
            name="거시 팩터 모델 (롤링 PCA, 00:20)",
            replace_existing=True,
        )
        # REQ-FH-EXT-CRON-01: 외국인 보유 일별 백필 (KST 18:00 평일).
        # 장 마감 15:30 + 데이터 확정 30분 여유 + KIS 야간 부하 회피.
        _scheduler.add_job(
            _run_foreign_holding_backfill_job,
            CronTrigger(hour=18, minute=0),
            id="foreign_holding_backfill",
            name="외국인 보유 추이 백필 (18:00)",
            replace_existing=True,
        )
        # 반도체 사이클 모니터링 (Phase 1) — 5 cron + 매시 평가.
        # 도메인: market_breadth/hbm_contracts는 KRX·DART 마감 후 / capex+inventory는 분기 멱등 매일
        # / ai_ipo는 매일 아침 / evaluate는 hourly (상태 변경 감지 + 토스트 트리거).
        _scheduler.add_job(
            _run_semi_collector_job,
            CronTrigger(day_of_week="mon-fri", hour=16, minute=0),
            args=["market_breadth"],
            id="semi_market_breadth",
            name="반도체 — KOSPI 시장폭 (평일 16:00)",
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_semi_collector_job,
            CronTrigger(day_of_week="mon-fri", hour=18, minute=30),
            args=["hbm_contracts"],
            id="semi_hbm_contracts",
            name="반도체 — HBM 공시 스캔 (평일 18:30)",
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_semi_collector_job,
            CronTrigger(hour=7, minute=0),
            args=["ai_ipo"],
            id="semi_ai_ipo",
            name="반도체 — AI IPO 추적 (07:00)",
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_semi_collector_job,
            CronTrigger(hour=8, minute=30),
            args=["hyperscaler_capex"],
            id="semi_hyperscaler_capex",
            name="반도체 — 하이퍼스케일러 capex (08:30 멱등)",
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_semi_collector_job,
            CronTrigger(hour=8, minute=35),
            args=["memory_inventory"],
            id="semi_memory_inventory",
            name="반도체 — 메모리 재고일수 (08:35 멱등)",
            replace_existing=True,
        )
        _scheduler.add_job(
            _run_semi_evaluate_job,
            CronTrigger(minute=0),  # 매시 정각
            id="semi_evaluate",
            name="반도체 — 시그널 평가 (매시 정각)",
            replace_existing=True,
        )
        # 2026-07-17: DB retention cleanup (KST 03:00).
        # append-only 로그/이력 9종 정리 → RDS 스토리지 비용 절감. 00:05 매크로
        # cleanup·00:20 팩터모델·파이프라인(08/16)과 시간대 분리, 트래픽 최저 구간.
        _scheduler.add_job(
            _run_db_retention_cleanup_job,
            CronTrigger(hour=3, minute=0),
            id="db_retention_cleanup",
            name="DB retention cleanup (03:00)",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(
            "[스케줄러] 스케줄러 시작 "
            "(08:00 KR / 16:00 US / 00:05 cleanup+prewarm / 18:00 FH backfill / "
            "반도체 5 cron + 매시 평가 / 03:00 retention)"
        )
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

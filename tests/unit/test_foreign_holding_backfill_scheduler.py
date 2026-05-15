"""REQ-FH-EXT-CRON-01: 외국인 보유 백필 cron 단위 테스트.

services/scheduler_service._run_foreign_holding_backfill_job() 검증:
- 토/일 weekday → 즉시 return + KIS 호출 0회
- 평일 + 활성 종목 N개 → fetch_foreign_holding N회 + sleep N회
- 50개 초과 → 50개로 truncate + logger.warning
- 종목 1개 예외 → 다른 종목 정상 진행 + raise 없음
- setup_scheduler 호출 시 foreign_holding_backfill 잡 등록
"""
from __future__ import annotations

import datetime as _dt
from unittest.mock import patch, MagicMock

import pytest


def _kst_wednesday() -> _dt.datetime:
    """확정 평일(2026-05-13 수요일 18:00 KST)."""
    return _dt.datetime(2026, 5, 13, 18, 0, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=9)))


def _kst_saturday() -> _dt.datetime:
    return _dt.datetime(2026, 5, 16, 18, 0, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=9)))


def _kst_sunday() -> _dt.datetime:
    return _dt.datetime(2026, 5, 17, 18, 0, 0, tzinfo=_dt.timezone(_dt.timedelta(hours=9)))


class TestWeekendSkip:

    def test_saturday_skips_all(self):
        from services import scheduler_service

        with patch.object(scheduler_service, "_now_kst", return_value=_kst_saturday()), \
             patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=[("005930", "KR")]), \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[]), \
             patch("services.supply_demand_service.fetch_foreign_holding") as m_fetch:
            scheduler_service._run_foreign_holding_backfill_job()

        # 토요일 → 활성 종목이 있어도 fetch 호출 0
        assert m_fetch.call_count == 0

    def test_sunday_skips_all(self):
        from services import scheduler_service

        with patch.object(scheduler_service, "_now_kst", return_value=_kst_sunday()), \
             patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=[("005930", "KR")]), \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[]), \
             patch("services.supply_demand_service.fetch_foreign_holding") as m_fetch:
            scheduler_service._run_foreign_holding_backfill_job()

        assert m_fetch.call_count == 0


class TestWeekdayRun:

    def test_weekday_calls_fetch_per_active_kr_code(self):
        from services import scheduler_service

        # advisory_stocks 2종목 (KR + US) → US 제외
        # watchlist 1종목 (KR, 겹치지 않는 코드) → 총 KR 2개
        with patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=[("005930", "KR"), ("AAPL", "US")], create=True) as _a, \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[("000660", "KR")], create=True) as _w, \
             patch.object(scheduler_service, "_now_kst", return_value=_kst_wednesday(), create=True), \
             patch("services.supply_demand_service.fetch_foreign_holding") as m_fetch, \
             patch("services.scheduler_service.time.sleep") as m_sleep:
            scheduler_service._run_foreign_holding_backfill_job()

        # KR 2종목만 fetch
        assert m_fetch.call_count == 2
        called_codes = sorted([c.args[0] for c in m_fetch.call_args_list])
        assert called_codes == ["000660", "005930"]
        # sleep 호출 (호출 사이)
        assert m_sleep.call_count == 2

    def test_dedup_advisory_and_watchlist_overlap(self):
        from services import scheduler_service

        with patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=[("005930", "KR")], create=True), \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[("005930", "KR")], create=True), \
             patch.object(scheduler_service, "_now_kst", return_value=_kst_wednesday(), create=True), \
             patch("services.supply_demand_service.fetch_foreign_holding") as m_fetch, \
             patch("services.scheduler_service.time.sleep"):
            scheduler_service._run_foreign_holding_backfill_job()
        # dedup → 1회만
        assert m_fetch.call_count == 1

    def test_cap_50_codes(self):
        from services import scheduler_service

        many = [(f"{i:06d}", "KR") for i in range(60)]
        with patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=many, create=True), \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[], create=True), \
             patch.object(scheduler_service, "_now_kst", return_value=_kst_wednesday(), create=True), \
             patch("services.supply_demand_service.fetch_foreign_holding") as m_fetch, \
             patch("services.scheduler_service.time.sleep"):
            scheduler_service._run_foreign_holding_backfill_job()
        # 50개 cap
        assert m_fetch.call_count == 50

    def test_per_stock_exception_does_not_abort(self):
        from services import scheduler_service

        codes = [("005930", "KR"), ("000660", "KR"), ("035720", "KR")]
        call_log = []

        def _fetch(code, days=30):
            call_log.append(code)
            if code == "000660":
                raise RuntimeError("simulated KIS failure")
            return {"ok": True}

        with patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=codes, create=True), \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[], create=True), \
             patch.object(scheduler_service, "_now_kst", return_value=_kst_wednesday(), create=True), \
             patch("services.supply_demand_service.fetch_foreign_holding", side_effect=_fetch), \
             patch("services.scheduler_service.time.sleep"):
            # raise 없이 끝나야 함 (다른 lifespan 잡 보호)
            scheduler_service._run_foreign_holding_backfill_job()

        # 모든 코드 시도(실패 무시)
        assert call_log == ["005930", "000660", "035720"]

    def test_no_active_codes_returns_quickly(self):
        from services import scheduler_service

        with patch("services.scheduler_service._all_advisory_users_codes",
                   return_value=[], create=True), \
             patch("services.scheduler_service._all_watchlist_codes",
                   return_value=[], create=True), \
             patch.object(scheduler_service, "_now_kst", return_value=_kst_wednesday(), create=True), \
             patch("services.supply_demand_service.fetch_foreign_holding") as m_fetch, \
             patch("services.scheduler_service.time.sleep") as m_sleep:
            scheduler_service._run_foreign_holding_backfill_job()
        assert m_fetch.call_count == 0
        assert m_sleep.call_count == 0


class TestSchedulerRegistration:

    def test_setup_scheduler_registers_backfill_job(self):
        """setup_scheduler 호출 시 foreign_holding_backfill 잡이 추가되는지."""
        from services import scheduler_service

        # apscheduler가 없을 수도 있으므로 BackgroundScheduler를 mock
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError:
            pytest.skip("apscheduler not installed")

        with patch.object(scheduler_service, "_scheduler", None):
            scheduler_service.setup_scheduler()
            sched = scheduler_service._scheduler
            assert sched is not None
            job_ids = {j.id for j in sched.get_jobs()}
            assert "foreign_holding_backfill" in job_ids
            scheduler_service.shutdown_scheduler()

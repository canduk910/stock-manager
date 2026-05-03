"""db/repositories/page_view_repo.py 통합 테스트."""

from datetime import datetime, timedelta, timezone

import pytest

KST = timezone(timedelta(hours=9))


def _record(repo, path: str, **kw):
    repo.record(
        user_id=kw.get("user_id"),
        path=path,
        method=kw.get("method", "GET"),
        status_code=kw.get("status_code", 200),
        duration_ms=kw.get("duration_ms", 12.5),
    )


class TestPageViewRepo:
    def test_record_inserts_row(self, db_session):
        from db.repositories.page_view_repo import PageViewRepository
        from db.models.page_view import PageView

        repo = PageViewRepository(db_session)
        _record(repo, "/api/balance", user_id=1)
        db_session.commit()
        rows = db_session.query(PageView).all()
        assert len(rows) == 1
        assert rows[0].path == "/api/balance"
        assert rows[0].user_id == 1
        assert rows[0].duration_ms > 0

    def test_aggregate_by_path_orders_desc(self, db_session):
        from db.repositories.page_view_repo import PageViewRepository
        repo = PageViewRepository(db_session)
        for _ in range(3):
            _record(repo, "/api/watchlist")
        for _ in range(7):
            _record(repo, "/api/balance")
        db_session.commit()

        today = datetime.now(KST).strftime("%Y-%m-%d")
        result = repo.aggregate_by_path(today, today, top=10)
        assert result[0]["path"] == "/api/balance"
        assert result[0]["calls"] == 7
        assert result[1]["path"] == "/api/watchlist"
        assert result[1]["calls"] == 3

    def test_aggregate_unique_users(self, db_session):
        from db.repositories.page_view_repo import PageViewRepository
        repo = PageViewRepository(db_session)
        _record(repo, "/api/x", user_id=1)
        _record(repo, "/api/x", user_id=1)
        _record(repo, "/api/x", user_id=2)
        db_session.commit()
        today = datetime.now(KST).strftime("%Y-%m-%d")
        result = repo.aggregate_by_path(today, today, top=10)
        assert result[0]["unique_users"] == 2

    def test_daily_timeseries_groups_by_date(self, db_session):
        from db.repositories.page_view_repo import PageViewRepository
        repo = PageViewRepository(db_session)
        for _ in range(2):
            _record(repo, "/api/foo")
        db_session.commit()
        today = datetime.now(KST).strftime("%Y-%m-%d")
        ts = repo.daily_timeseries(today, today, top=5)
        assert len(ts) >= 1
        assert ts[0]["date"] == today
        assert ts[0]["path"] == "/api/foo"

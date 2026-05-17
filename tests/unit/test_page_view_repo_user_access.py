"""사용자별 일별 접속현황 — PageViewRepository 3 메서드 단위 테스트.

REQ-REPO-1:
  - user_daily_timeseries(user_id, date_from, date_to) -> list[dict]
  - user_top_paths(user_id, date_from, date_to, top) -> list[dict]
  - user_last_seen_at(user_id) -> Optional[str]
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from db.models.page_view import PageView
from db.repositories.page_view_repo import PageViewRepository

KST = timezone(timedelta(hours=9))


def _ts(date_str: str, hour: int = 12, minute: int = 0, second: int = 0) -> str:
    """YYYY-MM-DD + HH:MM:SS → KST ISO string."""
    return f"{date_str}T{hour:02d}:{minute:02d}:{second:02d}+09:00"


def _insert_pv(db, *, user_id, path, created_at, method="GET", status_code=200, duration_ms=10.0):
    """created_at을 직접 지정해서 INSERT (PageView.record는 now_kst_iso 사용 → 과거 데이터 못 만듦)."""
    row = PageView(
        user_id=user_id,
        path=path,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        created_at=created_at,
    )
    db.add(row)
    db.flush()
    return row


# ─── user_daily_timeseries ──────────────────────────────────────────────────

class TestUserDailyTimeseries:
    def test_same_day_aggregation(self, db_session):
        """한 사용자 같은 날 3건(path A/B/A) → views=3, unique_paths=2."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts(today, 10))
        _insert_pv(db_session, user_id=1, path="/api/b", created_at=_ts(today, 11))
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts(today, 12))
        db_session.commit()

        result = repo.user_daily_timeseries(1, today, today)
        assert result == [{"date": today, "views": 3, "unique_paths": 2}]

    def test_excludes_other_users(self, db_session):
        """user=2 데이터는 user=1 시계열에 포함되지 않음."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        _insert_pv(db_session, user_id=2, path="/api/a", created_at=_ts(today, 10))
        db_session.commit()
        assert repo.user_daily_timeseries(1, today, today) == []

    def test_excludes_anonymous(self, db_session):
        """user_id IS NULL 행은 모든 사용자 시계열에서 제외."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        _insert_pv(db_session, user_id=None, path="/api/a", created_at=_ts(today, 10))
        _insert_pv(db_session, user_id=None, path="/api/b", created_at=_ts(today, 11))
        db_session.commit()
        assert repo.user_daily_timeseries(1, today, today) == []

    def test_multiple_days_sorted_asc(self, db_session):
        """여러 날에 걸친 데이터 → date asc 정렬, 누락된 날은 결과에 없음(라우터가 padding)."""
        repo = PageViewRepository(db_session)
        d1, d2, d3 = "2026-05-15", "2026-05-16", "2026-05-17"
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts(d1, 10))
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts(d3, 10))
        _insert_pv(db_session, user_id=1, path="/api/b", created_at=_ts(d3, 11))
        db_session.commit()

        result = repo.user_daily_timeseries(1, d1, d3)
        # d2 누락(repository는 padding 안 함)
        assert result == [
            {"date": d1, "views": 1, "unique_paths": 1},
            {"date": d3, "views": 2, "unique_paths": 2},
        ]

    def test_empty_result(self, db_session):
        """데이터 없으면 빈 리스트."""
        repo = PageViewRepository(db_session)
        assert repo.user_daily_timeseries(1, "2026-05-15", "2026-05-17") == []


# ─── user_top_paths ─────────────────────────────────────────────────────────

class TestUserTopPaths:
    def test_top_paths_desc_order(self, db_session):
        """[A,A,A,B,B] → [{A:3},{B:2}] views desc."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        for _ in range(3):
            _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts(today, 10))
        for _ in range(2):
            _insert_pv(db_session, user_id=1, path="/api/b", created_at=_ts(today, 11))
        db_session.commit()

        result = repo.user_top_paths(1, today, today, 5)
        assert result == [
            {"path": "/api/a", "views": 3},
            {"path": "/api/b", "views": 2},
        ]

    def test_top_paths_respects_limit(self, db_session):
        """limit=2이면 상위 2개만."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        for path, n in [("/api/a", 5), ("/api/b", 3), ("/api/c", 1)]:
            for _ in range(n):
                _insert_pv(db_session, user_id=1, path=path, created_at=_ts(today, 10))
        db_session.commit()

        result = repo.user_top_paths(1, today, today, 2)
        assert len(result) == 2
        assert [r["path"] for r in result] == ["/api/a", "/api/b"]

    def test_top_paths_excludes_other_users(self, db_session):
        """user=2의 path는 user=1 결과에 포함 안됨."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        _insert_pv(db_session, user_id=1, path="/api/own", created_at=_ts(today, 10))
        _insert_pv(db_session, user_id=2, path="/api/other", created_at=_ts(today, 10))
        db_session.commit()

        result = repo.user_top_paths(1, today, today, 5)
        paths = [r["path"] for r in result]
        assert "/api/own" in paths
        assert "/api/other" not in paths

    def test_top_paths_excludes_anonymous(self, db_session):
        """user_id IS NULL인 행은 어떤 사용자 top_paths에도 포함 안됨."""
        repo = PageViewRepository(db_session)
        today = "2026-05-17"
        _insert_pv(db_session, user_id=None, path="/api/anon", created_at=_ts(today, 10))
        db_session.commit()
        assert repo.user_top_paths(1, today, today, 5) == []

    def test_top_paths_empty(self, db_session):
        """데이터 없으면 빈 리스트."""
        repo = PageViewRepository(db_session)
        assert repo.user_top_paths(1, "2026-05-15", "2026-05-17", 5) == []

    def test_top_paths_respects_date_window(self, db_session):
        """window 외 데이터는 집계에 포함 안됨."""
        repo = PageViewRepository(db_session)
        in_day = "2026-05-17"
        out_day = "2026-05-10"
        _insert_pv(db_session, user_id=1, path="/api/in", created_at=_ts(in_day, 10))
        _insert_pv(db_session, user_id=1, path="/api/out", created_at=_ts(out_day, 10))
        db_session.commit()

        result = repo.user_top_paths(1, "2026-05-15", "2026-05-17", 5)
        paths = [r["path"] for r in result]
        assert "/api/in" in paths
        assert "/api/out" not in paths


# ─── user_last_seen_at ──────────────────────────────────────────────────────

class TestUserLastSeenAt:
    def test_returns_max_created_at(self, db_session):
        """전체 누계 중 가장 최신 created_at 반환."""
        repo = PageViewRepository(db_session)
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts("2026-05-15", 10))
        _insert_pv(db_session, user_id=1, path="/api/b", created_at=_ts("2026-05-17", 19, 30, 0))
        _insert_pv(db_session, user_id=1, path="/api/c", created_at=_ts("2026-05-16", 12))
        db_session.commit()

        result = repo.user_last_seen_at(1)
        assert result == _ts("2026-05-17", 19, 30, 0)

    def test_returns_none_for_unknown_user(self, db_session):
        """방문 기록 없는 사용자는 None."""
        repo = PageViewRepository(db_session)
        assert repo.user_last_seen_at(9999) is None

    def test_excludes_anonymous(self, db_session):
        """user=1 본인 기록만 고려; user_id IS NULL은 무관."""
        repo = PageViewRepository(db_session)
        _insert_pv(db_session, user_id=1, path="/api/own", created_at=_ts("2026-05-15", 10))
        _insert_pv(db_session, user_id=None, path="/api/anon", created_at=_ts("2026-05-20", 23))
        db_session.commit()

        result = repo.user_last_seen_at(1)
        assert result == _ts("2026-05-15", 10)

    def test_excludes_other_user(self, db_session):
        """다른 사용자(user=2) 기록은 user=1 last_seen에 포함 안됨."""
        repo = PageViewRepository(db_session)
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts("2026-05-15", 10))
        _insert_pv(db_session, user_id=2, path="/api/b", created_at=_ts("2026-05-20", 23))
        db_session.commit()
        assert repo.user_last_seen_at(1) == _ts("2026-05-15", 10)

    def test_no_date_filter(self, db_session):
        """days 범위 외 옛날 기록도 last_seen에 반영(전체 누계 기준 — 명세 확인)."""
        repo = PageViewRepository(db_session)
        very_old = "2024-01-01"
        _insert_pv(db_session, user_id=1, path="/api/a", created_at=_ts(very_old, 10))
        db_session.commit()
        assert repo.user_last_seen_at(1) == _ts(very_old, 10)

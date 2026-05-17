"""GET /api/admin/users/{user_id}/access-history — admin 사용자별 접속 이력.

REQ-API-1 + REQ-API-2 응답 shape/권한/검증 5+ 케이스.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from db.models.page_view import PageView
from db.repositories.user_repo import UserRepository

KST = timezone(timedelta(hours=9))


def _ts(date_str: str, hour: int = 12, minute: int = 0, second: int = 0) -> str:
    return f"{date_str}T{hour:02d}:{minute:02d}:{second:02d}+09:00"


def _today_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _days_ago(n: int) -> str:
    return (datetime.now(KST) - timedelta(days=n)).strftime("%Y-%m-%d")


def _insert_pv(db, *, user_id, path, created_at):
    row = PageView(
        user_id=user_id,
        path=path,
        method="GET",
        status_code=200,
        duration_ms=10.0,
        created_at=created_at,
    )
    db.add(row)
    db.flush()


# ─── fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def seeded_user(db_session):
    """alice 사용자(role=user) + PageView 데이터."""
    urepo = UserRepository(db_session)
    alice = urepo.create_user(
        username="alice", name="앨리스", hashed_password="x", role="user"
    )
    today = _today_str()
    one_ago = _days_ago(1)
    six_ago = _days_ago(6)

    # 오늘 3건 (path A 2회, path B 1회)
    _insert_pv(db_session, user_id=alice["id"], path="/api/a", created_at=_ts(today, 10))
    _insert_pv(db_session, user_id=alice["id"], path="/api/a", created_at=_ts(today, 11))
    _insert_pv(db_session, user_id=alice["id"], path="/api/b", created_at=_ts(today, 12))
    # 어제 1건
    _insert_pv(db_session, user_id=alice["id"], path="/api/a", created_at=_ts(one_ago, 10))
    # 6일 전 1건
    _insert_pv(db_session, user_id=alice["id"], path="/api/c", created_at=_ts(six_ago, 9))
    # anonymous 노이즈 (반드시 제외돼야 함)
    _insert_pv(db_session, user_id=None, path="/api/anon", created_at=_ts(today, 13))
    # 다른 사용자 노이즈 — 별도 user_id 99 (DB 없는 user_id지만 page_views.user_id는 외래키 아님)
    _insert_pv(db_session, user_id=99, path="/api/other", created_at=_ts(today, 14))

    db_session.commit()
    return alice


@pytest.fixture
def empty_user(db_session):
    """방문 0회 신규 사용자."""
    urepo = UserRepository(db_session)
    bob = urepo.create_user(
        username="bob", name="밥", hashed_password="x", role="user"
    )
    db_session.commit()
    return bob


# ─── 응답 shape 정상 ────────────────────────────────────────────────────────

class TestAccessHistoryBasic:
    def test_default_days_response_shape(self, client, seeded_user):
        """기본 days=30 → 응답 shape 필드 모두 존재."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history")
        assert res.status_code == 200, res.text
        body = res.json()

        # 필수 필드
        assert body["user_id"] == uid
        assert body["username"] == "alice"
        assert body["name"] == "앨리스"
        assert "last_seen_at" in body
        assert "total_views" in body
        assert body["days"] == 30
        assert "daily" in body
        assert "top_paths" in body

    def test_daily_length_matches_days(self, client, seeded_user):
        """daily 배열 길이가 days와 정확히 일치 (연속 시계열 padding)."""
        uid = seeded_user["id"]
        for days in (7, 30, 90, 180):
            res = client.get(f"/api/admin/users/{uid}/access-history?days={days}")
            assert res.status_code == 200
            body = res.json()
            assert len(body["daily"]) == days, f"days={days} but daily len={len(body['daily'])}"

    def test_daily_date_format_and_sorted(self, client, seeded_user):
        """daily[].date == YYYY-MM-DD + 오름차순."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=7")
        body = res.json()
        dates = [d["date"] for d in body["daily"]]
        # 포맷
        for d in dates:
            assert len(d) == 10 and d[4] == "-" and d[7] == "-"
        # 정렬
        assert dates == sorted(dates)

    def test_total_views_only_own(self, client, seeded_user):
        """total_views는 본인 누계만 (anonymous + 타 사용자 제외).

        seeded: alice 5건 (오늘 3 + 어제 1 + 6일전 1).
        """
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=30")
        body = res.json()
        assert body["total_views"] == 5

    def test_last_seen_at_present(self, client, seeded_user):
        """last_seen_at은 본인 가장 최신 created_at."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=30")
        body = res.json()
        assert body["last_seen_at"] is not None
        # 오늘 12시 PV(/api/b)가 최신 (anonymous 13시 + other 14시는 제외)
        assert body["last_seen_at"].startswith(_today_str())
        assert "T12:00:00" in body["last_seen_at"]

    def test_top_paths_desc(self, client, seeded_user):
        """top_paths views desc — /api/a가 1위 (오늘 2 + 어제 1 = 3건)."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=30")
        body = res.json()
        assert len(body["top_paths"]) >= 1
        assert body["top_paths"][0]["path"] == "/api/a"
        # views desc 정렬
        views = [p["views"] for p in body["top_paths"]]
        assert views == sorted(views, reverse=True)
        # anonymous /api/anon은 절대 포함 안됨
        paths = [p["path"] for p in body["top_paths"]]
        assert "/api/anon" not in paths
        assert "/api/other" not in paths

    def test_top_paths_respects_param(self, client, seeded_user):
        """top_paths=2이면 최대 2개."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=30&top_paths=2")
        body = res.json()
        assert len(body["top_paths"]) <= 2

    def test_daily_today_views_correct(self, client, seeded_user):
        """오늘 row는 본인 PV 3건 (anonymous + 타 user 제외)."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=30")
        body = res.json()
        today = _today_str()
        today_row = next(d for d in body["daily"] if d["date"] == today)
        assert today_row["views"] == 3
        assert today_row["unique_paths"] == 2  # /api/a, /api/b

    def test_daily_padding_zero(self, client, seeded_user):
        """데이터 없는 날도 views=0, unique_paths=0으로 채워짐."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=30")
        body = res.json()
        # 2일~5일 전은 데이터 없음 → 0
        for offset in (2, 3, 4, 5):
            target = _days_ago(offset)
            row = next(d for d in body["daily"] if d["date"] == target)
            assert row["views"] == 0
            assert row["unique_paths"] == 0


# ─── 빈 데이터 사용자 ─────────────────────────────────────────────────────────

class TestEmptyUser:
    def test_empty_user_zero_counts(self, client, empty_user):
        """방문 0회 사용자 → total_views=0, last_seen_at=null, top_paths=[], daily=모두 0."""
        uid = empty_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=7")
        assert res.status_code == 200
        body = res.json()

        assert body["total_views"] == 0
        assert body["last_seen_at"] is None
        assert body["top_paths"] == []
        assert len(body["daily"]) == 7
        for d in body["daily"]:
            assert d["views"] == 0
            assert d["unique_paths"] == 0


# ─── 권한/검증 ───────────────────────────────────────────────────────────────

class TestAccessHistoryGuards:
    def test_user_not_found_returns_404(self, client):
        """존재하지 않는 user_id → 404."""
        res = client.get("/api/admin/users/99999/access-history")
        assert res.status_code == 404
        body = res.json()
        assert "user_id=99999" in body["detail"]

    def test_days_below_min_returns_422(self, client, seeded_user):
        """days < 7 → FastAPI 422."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=5")
        assert res.status_code == 422

    def test_days_above_max_returns_422(self, client, seeded_user):
        """days > 180 → 422."""
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?days=200")
        assert res.status_code == 422

    def test_top_paths_below_min_returns_422(self, client, seeded_user):
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?top_paths=0")
        assert res.status_code == 422

    def test_top_paths_above_max_returns_422(self, client, seeded_user):
        uid = seeded_user["id"]
        res = client.get(f"/api/admin/users/{uid}/access-history?top_paths=25")
        assert res.status_code == 422

    def test_non_admin_returns_403(self, raw_client, db_session):
        """일반 사용자 토큰 → require_admin 의존성 → 403."""
        from services.auth_deps import get_current_user, require_admin
        from services.exceptions import ForbiddenError
        from main import app

        urepo = UserRepository(db_session)
        normal = urepo.create_user(
            username="normal", name="일반", hashed_password="x", role="user"
        )
        db_session.commit()

        # require_admin은 role!=admin이면 ForbiddenError(403). 일반 사용자 override.
        fake_user = {"id": normal["id"], "username": "normal", "name": "일반", "role": "user"}

        def _override_get_current_user():
            return fake_user

        def _override_require_admin():
            raise ForbiddenError("관리자 권한이 필요합니다.")

        app.dependency_overrides[get_current_user] = _override_get_current_user
        app.dependency_overrides[require_admin] = _override_require_admin
        try:
            res = raw_client.get(f"/api/admin/users/{normal['id']}/access-history")
            assert res.status_code == 403
        finally:
            app.dependency_overrides.clear()

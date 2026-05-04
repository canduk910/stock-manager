"""R4 (2026-05-04): GET /api/admin/users 응답에 visit_count 포함 검증 (API)."""

import pytest

from db.repositories.page_view_repo import PageViewRepository
from db.repositories.user_repo import UserRepository


@pytest.fixture
def seeded_users(db_session):
    """admin user 1명 + 일반 user 1명 + 방문 기록 셋업."""
    urepo = UserRepository(db_session)
    # admin (id=1, _FAKE_ADMIN과 매칭)
    admin = urepo.create_user(
        username="admin", name="관리자", hashed_password="x", role="admin"
    )
    user = urepo.create_user(
        username="alice", name="앨리스", hashed_password="x", role="user"
    )
    pv = PageViewRepository(db_session)
    for _ in range(4):
        pv.record(user_id=admin["id"], path="/api/x", method="GET", status_code=200, duration_ms=10)
    for _ in range(2):
        pv.record(user_id=user["id"], path="/api/y", method="GET", status_code=200, duration_ms=10)
    db_session.commit()
    return {"admin": admin, "user": user}


def test_admin_users_response_includes_visit_count(client, seeded_users):
    """GET /api/admin/users items 각 항목에 visit_count 포함."""
    res = client.get("/api/admin/users")
    assert res.status_code == 200
    body = res.json()
    items = body["items"]
    assert len(items) >= 2
    for item in items:
        assert "visit_count" in item
        assert isinstance(item["visit_count"], int)

    # 셋업한 카운트 검증
    by_username = {it["username"]: it for it in items}
    assert by_username["admin"]["visit_count"] == 4
    assert by_username["alice"]["visit_count"] == 2


def test_admin_user_detail_includes_visit_count(client, seeded_users):
    """GET /api/admin/users/{id} 응답에도 visit_count 포함."""
    user_id = seeded_users["user"]["id"]
    res = client.get(f"/api/admin/users/{user_id}")
    assert res.status_code == 200
    body = res.json()
    assert body.get("visit_count") == 2

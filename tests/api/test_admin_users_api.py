"""tests/api/test_admin_users_api.py — /api/admin/users 엔드포인트.

`client` fixture는 require_admin을 자동 우회 (conftest.py)."""


def _seed_users(db, n: int = 3):
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db)
    for i in range(n):
        repo.create_user(f"user{i}", f"User {i}", f"hashed{i}", role="user")
    db.commit()


def test_list_users_pagination(client, db_session):
    # admin 1명은 conftest의 _FAKE_ADMIN(id=1)이지만 실제 row는 없음 → repo로 직접 추가
    from db.repositories.user_repo import UserRepository
    UserRepository(db_session).create_user("admin", "관리자", "hash", role="admin")
    _seed_users(db_session, n=5)

    res = client.get("/api/admin/users?limit=3&offset=0")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 6
    assert len(data["items"]) == 3
    for item in data["items"]:
        assert "has_kis" in item
        assert item["has_kis"] is False  # 미등록 → False


def test_list_users_search(client, db_session):
    from db.repositories.user_repo import UserRepository
    UserRepository(db_session).create_user("alice", "Alice", "hash")
    UserRepository(db_session).create_user("bob", "Bob", "hash")
    db_session.commit()

    res = client.get("/api/admin/users?q=alic")
    assert res.status_code == 200
    items = res.json()["items"]
    usernames = [i["username"] for i in items]
    assert "alice" in usernames
    assert "bob" not in usernames


def test_get_user_not_found(client):
    res = client.get("/api/admin/users/99999")
    assert res.status_code == 404


def test_patch_user_role(client, db_session):
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    target = repo.create_user("toBeAdmin", "Up", "hash", role="user")
    db_session.commit()

    res = client.patch(f"/api/admin/users/{target['id']}", json={"role": "admin"})
    assert res.status_code == 200, res.text

    # 검증
    after = repo.get_by_id(target["id"])
    assert after["role"] == "admin"


def test_delete_user(client, db_session):
    from db.repositories.user_repo import UserRepository
    repo = UserRepository(db_session)
    target = repo.create_user("victim", "v", "hash")
    db_session.commit()

    res = client.delete(f"/api/admin/users/{target['id']}")
    assert res.status_code == 200

    assert repo.get_by_id(target["id"]) is None

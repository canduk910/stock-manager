"""tests/api/test_me_kis_api.py — /api/me/kis 엔드포인트.

검증 호출은 mocking. 실제 KIS API 호출 없음.
PostgreSQL FK 만족을 위해 매 테스트 시작 시 admin user row를 실제 INSERT하고,
get_current_user dependency override를 그 user의 실제 id로 동기화한다.
"""

import base64
import secrets
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)


@pytest.fixture
def authed_client(_test_engine):
    """admin user row를 실제 DB에 INSERT한 뒤, 그 id로 get_current_user를 override한
    TestClient. user_kis_credentials.user_id FK(→ users.id) 만족.

    conftest._make_client / client 패턴을 재현하되 _FAKE_ADMIN 대신 실제 id를 사용.
    """
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient

    from db.repositories.user_repo import UserRepository
    from db.base import Base
    from services.auth_deps import get_current_user, require_admin
    import db.session as _db_session_mod
    from main import app

    # 1) 사용자 row 시드 (별도 세션). 이전 테스트의 truncate 후 sequence가 reset되지
    #    않을 수 있으므로 SERIAL이 부여한 실제 id를 받아 그대로 사용.
    Session = sessionmaker(bind=_test_engine)
    seed_session = Session()
    try:
        repo = UserRepository(seed_session)
        admin_row = repo.create_user("admin", "관리자", "hash", role="admin")
        seed_session.commit()
        admin_id = admin_row["id"]
    finally:
        seed_session.close()

    fake_admin = {"id": admin_id, "username": "admin", "name": "관리자", "role": "admin"}

    # 2) SessionLocal을 테스트 엔진으로 교체 + dependency override
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=_test_engine)

    app.dependency_overrides[get_current_user] = lambda: fake_admin
    app.dependency_overrides[require_admin] = lambda: fake_admin

    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        _db_session_mod.SessionLocal.configure(bind=orig_bind)
        # 테스트 격리: 모든 테이블 truncate
        with _test_engine.connect() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
            conn.commit()


def _payload():
    return {
        "app_key": "REAL_APP_KEY_1234",
        "app_secret": "REAL_APP_SECRET_5678",
        "acnt_no": "12345678",
        "acnt_prdt_cd_stk": "01",
    }


def test_register_kis_validates_then_saves(authed_client):
    with patch("services.kis_validator.validate_kis", return_value=True) as m:
        res = authed_client.post("/api/me/kis", json=_payload())
    assert m.called
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_active"] is True
    assert body["validated_at"] is not None
    assert body["app_key_masked"].endswith("1234")
    # app_secret/acnt_no는 응답에 포함 안 됨
    assert "app_secret" not in body
    assert "acnt_no" not in body


def test_register_kis_validation_failure_returns_502(authed_client):
    from services.exceptions import ExternalAPIError
    with patch("services.kis_validator.validate_kis", side_effect=ExternalAPIError("invalid")):
        res = authed_client.post("/api/me/kis", json=_payload())
    assert res.status_code == 502


def test_get_kis_unregistered_returns_registered_false(authed_client):
    res = authed_client.get("/api/me/kis")
    assert res.status_code == 200
    body = res.json()
    assert body["registered"] is False
    assert body["is_active"] is False


def test_register_then_get_returns_masked(authed_client):
    with patch("services.kis_validator.validate_kis", return_value=True):
        authed_client.post("/api/me/kis", json=_payload())

    res = authed_client.get("/api/me/kis")
    assert res.status_code == 200
    body = res.json()
    assert body["registered"] is True
    assert body["app_key_masked"].endswith("1234")
    assert body["is_active"] is True


def test_delete_kis(authed_client):
    with patch("services.kis_validator.validate_kis", return_value=True):
        authed_client.post("/api/me/kis", json=_payload())
    res = authed_client.delete("/api/me/kis")
    assert res.status_code == 200
    # 재조회 시 등록 X
    after = authed_client.get("/api/me/kis").json()
    assert after["registered"] is False


def test_validate_endpoint_re_marks_validated(authed_client):
    with patch("services.kis_validator.validate_kis", return_value=True):
        authed_client.post("/api/me/kis", json=_payload())

    with patch("services.kis_validator.validate_kis", return_value=True):
        res = authed_client.post("/api/me/kis/validate")
    assert res.status_code == 200
    assert res.json()["is_active"] is True

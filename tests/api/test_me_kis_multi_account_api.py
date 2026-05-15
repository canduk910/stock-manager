"""R3 (KIS 멀티 계좌) — /api/me/kis 멀티 계좌 CRUD 6 라우트 통합 테스트.

요건 REQ-API-01:
- POST  /api/me/kis              body={label, is_default?, app_key, ...} → 201
- GET   /api/me/kis              → 200 + {accounts:[...], default_label, ...}
- GET   /api/me/kis/{label}      → 200 / 404
- PUT   /api/me/kis/{label}      → 라벨 변경 + 자격증명 갱신, 자격증명 변경 시 자동 재검증
- DELETE /api/me/kis/{label}     → 200, default 삭제 시 자동 승격
- POST  /api/me/kis/{label}/default   → is_default 전환
- POST  /api/me/kis/{label}/validate  → 재검증

도메인 가드:
- 첫 계좌는 is_default=true 자동 강제 (body 무시).
- 라벨 중복 시 409 ConflictError.
- 라벨 없음 404 NotFoundError.
- 0계좌 GET → registered=False, accounts=[], default_label=None.
- 마지막 1개 DELETE 허용.
- 라벨 길이 51자 → 400/422.
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
    """관리자 user row 실제 INSERT + dependency override."""
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient
    from db.repositories.user_repo import UserRepository
    from db.base import Base
    from services.auth_deps import get_current_user, require_admin
    import db.session as _db_session_mod
    from main import app

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
        with _test_engine.connect() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
            conn.commit()


def _body(label="주식", *, app_key="REAL_KEY_1234", is_default=None):
    p = {
        "label": label,
        "app_key": app_key,
        "app_secret": "REAL_SECRET_5678",
        "acnt_no": "12345678",
        "acnt_prdt_cd_stk": "01",
    }
    if is_default is not None:
        p["is_default"] = is_default
    return p


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/me/kis
# ──────────────────────────────────────────────────────────────────────────────


class TestPostMultiAccount:
    def test_first_account_auto_default(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            res = authed_client.post("/api/me/kis", json=_body(is_default=False))
        assert res.status_code in (200, 201), res.text
        body = res.json()
        # 첫 계좌는 무조건 default (body의 is_default=False 무시)
        assert body["is_default"] is True
        assert body["label"] == "주식"

    def test_label_conflict_returns_409(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="주식"))
            res = authed_client.post("/api/me/kis", json=_body(label="주식"))
        assert res.status_code == 409, res.text

    def test_validation_failure_returns_502(self, authed_client):
        from services.exceptions import ExternalAPIError
        with patch("services.kis_validator.validate_kis", side_effect=ExternalAPIError("bad")):
            res = authed_client.post("/api/me/kis", json=_body())
        assert res.status_code == 502

    def test_label_max_length_50(self, authed_client):
        long_label = "x" * 51
        with patch("services.kis_validator.validate_kis", return_value=True):
            res = authed_client.post("/api/me/kis", json=_body(label=long_label))
        # Pydantic max_length=50 → 422; 또는 400 ServiceError 도 허용.
        assert res.status_code in (400, 422), res.text


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/me/kis
# ──────────────────────────────────────────────────────────────────────────────


class TestGetMultiAccount:
    def test_zero_accounts(self, authed_client):
        res = authed_client.get("/api/me/kis")
        assert res.status_code == 200
        body = res.json()
        assert body.get("accounts") == []
        assert body.get("default_label") is None
        # 백워드 호환 키
        assert body["registered"] is False
        assert body["is_active"] is False

    def test_list_accounts(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="주식", app_key="K1_111122223333"))
            authed_client.post("/api/me/kis", json=_body(label="연금", app_key="K2_444455556666"))

        res = authed_client.get("/api/me/kis")
        assert res.status_code == 200
        body = res.json()
        accounts = body["accounts"]
        assert len(accounts) == 2
        labels = {a["label"] for a in accounts}
        assert labels == {"주식", "연금"}
        assert body["default_label"] == "주식"
        # 마스킹
        for a in accounts:
            assert "app_secret" not in a
            assert "acnt_no" not in a
            assert "app_key_masked" in a
            assert "acnt_no_masked" in a
            assert "is_default" in a
            assert "fno_enabled" in a

    def test_get_single_by_label(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="주식"))
        res = authed_client.get("/api/me/kis/주식")
        assert res.status_code == 200
        body = res.json()
        assert body["label"] == "주식"
        assert "app_key_masked" in body

    def test_get_single_not_found(self, authed_client):
        res = authed_client.get("/api/me/kis/없는라벨")
        assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/me/kis/{label}
# ──────────────────────────────────────────────────────────────────────────────


class TestPutMultiAccount:
    def test_rename_label(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="A"))
            res = authed_client.put("/api/me/kis/A", json={"label": "C"})
        assert res.status_code == 200, res.text
        assert res.json()["label"] == "C"
        # 기존 라벨 조회 시 404
        assert authed_client.get("/api/me/kis/A").status_code == 404
        assert authed_client.get("/api/me/kis/C").status_code == 200

    def test_update_credentials_forces_revalidate(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="주식"))

        # 자격증명 변경 — 자동 재검증 (성공)
        with patch("services.kis_validator.validate_kis", return_value=True):
            res = authed_client.put(
                "/api/me/kis/주식",
                json={"app_key": "NEW_KEY_44445555"},
            )
        assert res.status_code == 200
        body = res.json()
        assert body["app_key_masked"].endswith("5555")
        assert body["is_active"] is True

    def test_rename_to_existing_label_returns_409(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="A"))
            authed_client.post("/api/me/kis", json=_body(label="B"))
            res = authed_client.put("/api/me/kis/A", json={"label": "B"})
        assert res.status_code == 409

    def test_update_not_found_returns_404(self, authed_client):
        # app_key 는 min_length=8 — 8자 이상으로 보내 Pydantic 검증 통과 후 라우터에서 404 발생.
        res = authed_client.put("/api/me/kis/없음", json={"app_key": "VALID_KEY_8CHARS"})
        assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /api/me/kis/{label}
# ──────────────────────────────────────────────────────────────────────────────


class TestDeleteMultiAccount:
    def test_delete_default_auto_promotes(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="A"))  # default
            authed_client.post("/api/me/kis", json=_body(label="B"))
        res = authed_client.delete("/api/me/kis/A")
        assert res.status_code == 200
        # B 가 default 로 승격
        listing = authed_client.get("/api/me/kis").json()
        assert listing["default_label"] == "B"

    def test_delete_last_allows_zero(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="X"))
        res = authed_client.delete("/api/me/kis/X")
        assert res.status_code == 200
        assert authed_client.get("/api/me/kis").json()["accounts"] == []

    def test_delete_not_found_returns_404(self, authed_client):
        res = authed_client.delete("/api/me/kis/없음")
        assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/me/kis/{label}/default
# ──────────────────────────────────────────────────────────────────────────────


class TestSetDefault:
    def test_set_default_switches(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="A"))
            authed_client.post("/api/me/kis", json=_body(label="B"))
        res = authed_client.post("/api/me/kis/B/default")
        assert res.status_code == 200
        listing = authed_client.get("/api/me/kis").json()
        assert listing["default_label"] == "B"

    def test_set_default_not_found(self, authed_client):
        res = authed_client.post("/api/me/kis/없음/default")
        assert res.status_code == 404


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/me/kis/{label}/validate
# ──────────────────────────────────────────────────────────────────────────────


class TestValidateEndpoint:
    def test_validate_per_label(self, authed_client):
        with patch("services.kis_validator.validate_kis", return_value=True):
            authed_client.post("/api/me/kis", json=_body(label="주식"))
            res = authed_client.post("/api/me/kis/주식/validate")
        assert res.status_code == 200
        assert res.json()["is_active"] is True

    def test_validate_not_found(self, authed_client):
        res = authed_client.post("/api/me/kis/없음/validate")
        assert res.status_code == 404

"""tests/api/test_me_kis_api.py — /api/me/kis 엔드포인트.

검증 호출은 mocking. 실제 KIS API 호출 없음.
"""

import base64
import secrets
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _set_master_key(monkeypatch):
    key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)


def _payload():
    return {
        "app_key": "REAL_APP_KEY_1234",
        "app_secret": "REAL_APP_SECRET_5678",
        "acnt_no": "12345678",
        "acnt_prdt_cd_stk": "01",
    }


def test_register_kis_validates_then_saves(client):
    with patch("services.kis_validator.validate_kis", return_value=True) as m:
        res = client.post("/api/me/kis", json=_payload())
    assert m.called
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["is_active"] is True
    assert body["validated_at"] is not None
    assert body["app_key_masked"].endswith("1234")
    # app_secret/acnt_no는 응답에 포함 안 됨
    assert "app_secret" not in body
    assert "acnt_no" not in body


def test_register_kis_validation_failure_returns_502(client):
    from services.exceptions import ExternalAPIError
    with patch("services.kis_validator.validate_kis", side_effect=ExternalAPIError("invalid")):
        res = client.post("/api/me/kis", json=_payload())
    assert res.status_code == 502


def test_get_kis_unregistered_returns_registered_false(client):
    res = client.get("/api/me/kis")
    assert res.status_code == 200
    body = res.json()
    assert body["registered"] is False
    assert body["is_active"] is False


def test_register_then_get_returns_masked(client):
    with patch("services.kis_validator.validate_kis", return_value=True):
        client.post("/api/me/kis", json=_payload())

    res = client.get("/api/me/kis")
    assert res.status_code == 200
    body = res.json()
    assert body["registered"] is True
    assert body["app_key_masked"].endswith("1234")
    assert body["is_active"] is True


def test_delete_kis(client):
    with patch("services.kis_validator.validate_kis", return_value=True):
        client.post("/api/me/kis", json=_payload())
    res = client.delete("/api/me/kis")
    assert res.status_code == 200
    # 재조회 시 등록 X
    after = client.get("/api/me/kis").json()
    assert after["registered"] is False


def test_validate_endpoint_re_marks_validated(client):
    with patch("services.kis_validator.validate_kis", return_value=True):
        client.post("/api/me/kis", json=_payload())

    with patch("services.kis_validator.validate_kis", return_value=True):
        res = client.post("/api/me/kis/validate")
    assert res.status_code == 200
    assert res.json()["is_active"] is True

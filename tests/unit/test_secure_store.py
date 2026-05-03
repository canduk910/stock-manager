"""services/secure_store.py — AES-GCM 암호화 모듈 단위 테스트."""

from __future__ import annotations

import base64
import os
import secrets
from typing import Optional

import pytest


def _set_master_key(monkeypatch, key_b64: Optional[str] = None):
    """secure_store가 import 시점에 마스터 키를 캡처하지 않도록 함수 호출 시 env에서 읽게 한다."""
    if key_b64 is None:
        # 32-byte 랜덤 키 → urlsafe b64
        key_b64 = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
    monkeypatch.setenv("KIS_ENCRYPTION_KEY", key_b64)
    return key_b64


class TestSecureStoreRoundTrip:
    def test_encrypt_decrypt_basic(self, monkeypatch):
        _set_master_key(monkeypatch)
        from services import secure_store
        cipher = secure_store.encrypt("hello-secret")
        assert cipher != "hello-secret"
        assert secure_store.decrypt(cipher) == "hello-secret"

    def test_encrypt_korean_unicode(self, monkeypatch):
        _set_master_key(monkeypatch)
        from services import secure_store
        plaintext = "한국투자증권-비밀-키-12345"
        cipher = secure_store.encrypt(plaintext)
        assert secure_store.decrypt(cipher) == plaintext

    def test_encrypt_long_string(self, monkeypatch):
        _set_master_key(monkeypatch)
        from services import secure_store
        plaintext = "x" * 4096
        cipher = secure_store.encrypt(plaintext)
        assert secure_store.decrypt(cipher) == plaintext

    def test_encrypt_empty_string(self, monkeypatch):
        _set_master_key(monkeypatch)
        from services import secure_store
        cipher = secure_store.encrypt("")
        assert secure_store.decrypt(cipher) == ""

    def test_nonce_unique_per_encrypt(self, monkeypatch):
        """매 호출마다 12-byte nonce가 새로 생성되어 cipher가 달라야 한다."""
        _set_master_key(monkeypatch)
        from services import secure_store
        c1 = secure_store.encrypt("same-text")
        c2 = secure_store.encrypt("same-text")
        assert c1 != c2
        assert secure_store.decrypt(c1) == "same-text"
        assert secure_store.decrypt(c2) == "same-text"


class TestSecureStoreFailures:
    def test_missing_master_key_raises_config_error(self, monkeypatch):
        from services.exceptions import ConfigError
        monkeypatch.delenv("KIS_ENCRYPTION_KEY", raising=False)
        from services import secure_store
        with pytest.raises(ConfigError):
            secure_store.encrypt("anything")

    def test_decrypt_with_different_key_fails(self, monkeypatch):
        from services.exceptions import ServiceError
        _set_master_key(monkeypatch)
        from services import secure_store
        cipher = secure_store.encrypt("hello")

        # 다른 키로 교체
        new_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
        monkeypatch.setenv("KIS_ENCRYPTION_KEY", new_key)
        with pytest.raises(Exception):  # InvalidTag or ServiceError
            secure_store.decrypt(cipher)

    def test_decrypt_invalid_b64_raises(self, monkeypatch):
        _set_master_key(monkeypatch)
        from services import secure_store
        with pytest.raises(Exception):
            secure_store.decrypt("not-valid-b64!@#$")

    def test_decrypt_too_short_ciphertext_raises(self, monkeypatch):
        _set_master_key(monkeypatch)
        from services import secure_store
        # nonce(12) 미만이면 형식 오류
        too_short = base64.urlsafe_b64encode(b"short").decode("ascii")
        with pytest.raises(Exception):
            secure_store.decrypt(too_short)

"""AES-GCM 기반 사용자별 KIS 자격증명 암호화 모듈.

마스터 키: env `KIS_ENCRYPTION_KEY` (urlsafe-base64 32-byte). 미설정 시 ConfigError(503).

저장 포맷: `urlsafe_b64( nonce[12] || ciphertext_with_tag )` — 단일 b64 문자열.

cryptography>=42 의 AESGCM 사용 — 표준 GCM(16-byte tag 자동 부착).
"""

from __future__ import annotations

import base64
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from services.exceptions import ConfigError, ServiceError


def _load_master_key() -> bytes:
    """env에서 마스터 키 로드. 미설정/형식 오류 시 ConfigError."""
    raw = os.getenv("KIS_ENCRYPTION_KEY", "")
    if not raw:
        raise ConfigError(
            "KIS_ENCRYPTION_KEY 환경변수가 설정되지 않았습니다. "
            "32-byte 키를 urlsafe-base64로 인코딩해 .env에 등록하세요. "
            "발급 방법: python -c \"import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
        )
    try:
        key = base64.urlsafe_b64decode(raw.encode("ascii"))
    except Exception as e:
        raise ConfigError(f"KIS_ENCRYPTION_KEY 디코드 실패: {e}")
    if len(key) != 32:
        raise ConfigError(
            f"KIS_ENCRYPTION_KEY 길이 오류: 32 byte 필요, 현재 {len(key)} byte"
        )
    return key


def encrypt(plaintext: str) -> str:
    """평문 문자열을 AES-GCM으로 암호화하여 urlsafe-b64 문자열 반환."""
    key = _load_master_key()
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    blob = nonce + ct
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt(ciphertext_b64: str) -> str:
    """urlsafe-b64 암호문을 복호화하여 평문 문자열 반환.

    실패 시 ServiceError 또는 cryptography.InvalidTag 가 raise 될 수 있다.
    """
    key = _load_master_key()
    try:
        blob = base64.urlsafe_b64decode(ciphertext_b64.encode("ascii"))
    except Exception as e:
        raise ServiceError(f"암호문 디코드 실패: {e}")
    if len(blob) < 12 + 16:  # nonce + 최소 GCM tag
        raise ServiceError("암호문 길이 오류")
    nonce, ct = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    try:
        pt = aesgcm.decrypt(nonce, ct, associated_data=None)
    except InvalidTag:
        # 키가 다르거나 tampered
        raise ServiceError("암호문 무결성 검증 실패")
    return pt.decode("utf-8")

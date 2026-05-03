"""UserKisRepository — 사용자별 KIS 자격증명 CRUD + 검증 상태 관리.

- 모든 민감 필드(app_key, app_secret, acnt_no)는 secure_store로 암호화/복호화.
- get() 은 plaintext dict 반환(라우터/서비스 사용용). DB row 직접 노출 금지.
- mark_validated(): 검증 시각(KST ISO) 기록 → is_valid()는 KIS_VALIDATION_TTL_HOURS 이내만 True.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models.user_kis import UserKisCredentials
from db.utils import KST, now_kst_iso
from services import secure_store


def _validation_ttl_hours() -> float:
    return float(os.getenv("KIS_VALIDATION_TTL_HOURS", "24"))


def _parse_iso_kst(s: str) -> datetime:
    """KST ISO 문자열 파싱. timezone-naive 인 경우 KST 부착."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt


class UserKisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: int) -> Optional[dict]:
        """plaintext dict 반환. 미등록 시 None."""
        row = self.db.query(UserKisCredentials).filter_by(user_id=user_id).first()
        if not row:
            return None
        return {
            "user_id": row.user_id,
            "app_key": secure_store.decrypt(row.app_key_enc),
            "app_secret": secure_store.decrypt(row.app_secret_enc),
            "acnt_no": secure_store.decrypt(row.acnt_no_enc),
            "acnt_prdt_cd_stk": row.acnt_prdt_cd_stk,
            "acnt_prdt_cd_fno": row.acnt_prdt_cd_fno,
            "hts_id": row.hts_id,
            "base_url": row.base_url,
            "validated_at": row.validated_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def get_masked(self, user_id: int) -> Optional[dict]:
        """app_key 끝 4자리만 노출, app_secret/acnt_no 미노출. 응답용."""
        row = self.db.query(UserKisCredentials).filter_by(user_id=user_id).first()
        if not row:
            return None
        try:
            app_key_plain = secure_store.decrypt(row.app_key_enc)
            masked = "X" * max(0, len(app_key_plain) - 4) + app_key_plain[-4:]
        except Exception:
            masked = "********"
        return {
            "user_id": row.user_id,
            "app_key_masked": masked,
            "acnt_prdt_cd_stk": row.acnt_prdt_cd_stk,
            "acnt_prdt_cd_fno": row.acnt_prdt_cd_fno,
            "hts_id": row.hts_id,
            "base_url": row.base_url,
            "validated_at": row.validated_at,
            "is_active": self._is_valid_row(row),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def upsert(self, user_id: int, kis: dict) -> None:
        """등록/갱신. plaintext dict를 받아 암호화 후 저장.

        kis 키: app_key, app_secret, acnt_no, acnt_prdt_cd_stk,
                acnt_prdt_cd_fno?, hts_id?, base_url?
        """
        now = now_kst_iso()
        base_url = kis.get("base_url") or "https://openapi.koreainvestment.com:9443"
        row = self.db.query(UserKisCredentials).filter_by(user_id=user_id).first()
        if row:
            row.app_key_enc = secure_store.encrypt(kis["app_key"])
            row.app_secret_enc = secure_store.encrypt(kis["app_secret"])
            row.acnt_no_enc = secure_store.encrypt(kis["acnt_no"])
            row.acnt_prdt_cd_stk = kis["acnt_prdt_cd_stk"]
            row.acnt_prdt_cd_fno = kis.get("acnt_prdt_cd_fno")
            row.hts_id = kis.get("hts_id")
            row.base_url = base_url
            row.updated_at = now
            # validated_at은 mark_validated()에서만 갱신 (자격증명만 변경 시 재검증 강제)
            row.validated_at = None
        else:
            row = UserKisCredentials(
                user_id=user_id,
                app_key_enc=secure_store.encrypt(kis["app_key"]),
                app_secret_enc=secure_store.encrypt(kis["app_secret"]),
                acnt_no_enc=secure_store.encrypt(kis["acnt_no"]),
                acnt_prdt_cd_stk=kis["acnt_prdt_cd_stk"],
                acnt_prdt_cd_fno=kis.get("acnt_prdt_cd_fno"),
                hts_id=kis.get("hts_id"),
                base_url=base_url,
                validated_at=None,
                created_at=now,
                updated_at=now,
            )
            self.db.add(row)
        self.db.flush()

    def delete(self, user_id: int) -> bool:
        count = self.db.query(UserKisCredentials).filter_by(user_id=user_id).delete()
        return count > 0

    def mark_validated(self, user_id: int) -> None:
        row = self.db.query(UserKisCredentials).filter_by(user_id=user_id).first()
        if row:
            row.validated_at = now_kst_iso()
            self.db.flush()

    def _is_valid_row(self, row: UserKisCredentials) -> bool:
        if not row.validated_at:
            return False
        try:
            ts = _parse_iso_kst(row.validated_at)
        except Exception:
            return False
        return datetime.now(KST) - ts <= timedelta(hours=_validation_ttl_hours())

    def is_valid(self, user_id: int) -> bool:
        """KIS_VALIDATION_TTL_HOURS 이내에 검증된 자격증명이 등록되어 있으면 True."""
        row = self.db.query(UserKisCredentials).filter_by(user_id=user_id).first()
        if not row:
            return False
        return self._is_valid_row(row)

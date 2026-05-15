"""UserKisRepository — 사용자별 KIS 자격증명 CRUD (R1: 1:N 멀티 계좌).

- 모든 민감 필드(app_key, app_secret, acnt_no)는 secure_store 로 암호화/복호화.
- 멀티 계좌 신규 API:
    list_accounts / get_by_label / get_default / create_account / update_account /
    delete_account / set_default / mark_validated_label / is_valid_label
- 백워드 호환 API (default 계좌 의미로 재정의):
    get / upsert / delete / mark_validated / is_valid

도메인 가드:
- 사용자당 라벨 중복 금지 (`UNIQUE(user_id, label)`) — 중복 시 ConflictError.
- 사용자당 is_default=true 행 최대 1개 — 새 default 설정 시 다른 default 자동 강등.
- 첫 계좌 등록 시 is_default 자동 강제 true.
- default 계좌 삭제 시 남은 계좌 1개를 자동 default 승격.
- 마지막 1개 삭제도 허용 (0개 상태 OK).
- 라우터/서비스에서 HTTPException 직접 raise 금지 — `ConflictError(409)` / `NotFoundError(404)` 사용.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from db.models.user_kis import UserKisCredentials
from db.utils import KST, now_kst_iso
from services import secure_store
from services.exceptions import ConflictError, NotFoundError


def _validation_ttl_hours() -> float:
    return float(os.getenv("KIS_VALIDATION_TTL_HOURS", "24"))


def _parse_iso_kst(s: str) -> datetime:
    """KST ISO 문자열 파싱. timezone-naive 인 경우 KST 부착."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt


# ──────────────────────────────────────────────────────────────────────────────
# 라벨 시드 — 기존 1행 사용자(`upsert(user_id, kis)`) 호출자가 라벨 미지정 시 '기본'.
# ──────────────────────────────────────────────────────────────────────────────
_DEFAULT_LABEL_FALLBACK = "기본"


class UserKisRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── helpers ─────────────────────────────────────────────────────

    def _row_to_dict(self, row: UserKisCredentials) -> dict:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "label": row.label,
            "is_default": bool(row.is_default),
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

    def _row_to_masked(self, row: UserKisCredentials) -> dict:
        try:
            app_key_plain = secure_store.decrypt(row.app_key_enc)
            app_key_masked = "X" * max(0, len(app_key_plain) - 4) + app_key_plain[-4:]
        except Exception:
            app_key_masked = "********"
        try:
            acnt_plain = secure_store.decrypt(row.acnt_no_enc)
            if len(acnt_plain) >= 4:
                acnt_masked = f"{acnt_plain[:2]}****{acnt_plain[-2:]}"
            else:
                acnt_masked = "********"
        except Exception:
            acnt_masked = "********"
        return {
            "id": row.id,
            "user_id": row.user_id,
            "label": row.label,
            "is_default": bool(row.is_default),
            "app_key_masked": app_key_masked,
            "acnt_no_masked": acnt_masked,
            "acnt_prdt_cd_stk": row.acnt_prdt_cd_stk,
            "acnt_prdt_cd_fno": row.acnt_prdt_cd_fno,
            "fno_enabled": bool(row.acnt_prdt_cd_fno),
            "hts_id": row.hts_id,
            "base_url": row.base_url,
            "validated_at": row.validated_at,
            "is_active": self._is_valid_row(row),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    def _is_valid_row(self, row: UserKisCredentials) -> bool:
        if not row.validated_at:
            return False
        try:
            ts = _parse_iso_kst(row.validated_at)
        except Exception:
            return False
        return datetime.now(KST) - ts <= timedelta(hours=_validation_ttl_hours())

    def _clear_other_defaults(self, user_id: int, except_row_id: Optional[int] = None) -> None:
        """user_id 내 다른 default 행을 is_default=false 로 강등."""
        q = (
            self.db.query(UserKisCredentials)
            .filter(UserKisCredentials.user_id == user_id, UserKisCredentials.is_default.is_(True))
        )
        if except_row_id is not None:
            q = q.filter(UserKisCredentials.id != except_row_id)
        for r in q.all():
            r.is_default = False

    # ── 신규 멀티 계좌 API ──────────────────────────────────────────

    def list_accounts(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id)
            .order_by(UserKisCredentials.id.asc())
            .all()
        )
        return [self._row_to_dict(r) for r in rows]

    def list_accounts_masked(self, user_id: int) -> list[dict]:
        rows = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id)
            .order_by(UserKisCredentials.id.asc())
            .all()
        )
        return [self._row_to_masked(r) for r in rows]

    def get_by_label(self, user_id: int, label: str) -> Optional[dict]:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        return self._row_to_dict(row) if row else None

    def get_masked_by_label(self, user_id: int, label: str) -> Optional[dict]:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        return self._row_to_masked(row) if row else None

    def get_default(self, user_id: int) -> Optional[dict]:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, is_default=True)
            .first()
        )
        if row:
            return self._row_to_dict(row)
        # default 부재 시 가장 오래된 row 1개 자동 폴백 (방어적 — 불변식 깨진 데이터)
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id)
            .order_by(UserKisCredentials.id.asc())
            .first()
        )
        return self._row_to_dict(row) if row else None

    def create_account(self, user_id: int, kis: dict) -> dict:
        """새 KIS 계좌 행 추가.

        kis 키: label, is_default?, app_key, app_secret, acnt_no, acnt_prdt_cd_stk,
                acnt_prdt_cd_fno?, hts_id?, base_url?
        라벨 중복 시 ConflictError. 첫 계좌는 무조건 is_default=true.
        """
        label = kis.get("label") or _DEFAULT_LABEL_FALLBACK
        # 라벨 중복 검사 (선제) — UNIQUE 위반 IntegrityError 보다 친화적인 ConflictError 변환.
        existing = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        if existing:
            raise ConflictError(f"동일한 라벨이 이미 존재합니다: {label}")

        # 첫 계좌면 무조건 default, 아니면 body 값 존중 (true 면 다른 default 강등).
        existing_count = (
            self.db.query(UserKisCredentials).filter_by(user_id=user_id).count()
        )
        is_default = bool(kis.get("is_default"))
        if existing_count == 0:
            is_default = True
        elif is_default:
            self._clear_other_defaults(user_id)

        now = now_kst_iso()
        base_url = kis.get("base_url") or "https://openapi.koreainvestment.com:9443"
        row = UserKisCredentials(
            user_id=user_id,
            label=label,
            is_default=is_default,
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
        return self._row_to_dict(row)

    def update_account(self, user_id: int, label: str, partial: dict) -> dict:
        """기존 계좌의 자격증명/라벨 갱신.

        partial 가능 키: label, app_key, app_secret, acnt_no, acnt_prdt_cd_stk,
                        acnt_prdt_cd_fno, hts_id, base_url.
        자격증명 변경 시 validated_at 자동 해제 (재검증 강제).
        """
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        if not row:
            raise NotFoundError(f"라벨 '{label}' 의 계좌를 찾을 수 없습니다.")

        sensitive_changed = False
        new_label = partial.get("label")
        if new_label is not None and new_label != label:
            # 라벨 변경 충돌 검사
            conflict = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id, label=new_label)
                .first()
            )
            if conflict:
                raise ConflictError(f"동일한 라벨이 이미 존재합니다: {new_label}")
            row.label = new_label

        if "app_key" in partial and partial["app_key"]:
            row.app_key_enc = secure_store.encrypt(partial["app_key"])
            sensitive_changed = True
        if "app_secret" in partial and partial["app_secret"]:
            row.app_secret_enc = secure_store.encrypt(partial["app_secret"])
            sensitive_changed = True
        if "acnt_no" in partial and partial["acnt_no"]:
            row.acnt_no_enc = secure_store.encrypt(partial["acnt_no"])
            sensitive_changed = True
        if "acnt_prdt_cd_stk" in partial and partial["acnt_prdt_cd_stk"]:
            row.acnt_prdt_cd_stk = partial["acnt_prdt_cd_stk"]
        if "acnt_prdt_cd_fno" in partial:
            row.acnt_prdt_cd_fno = partial["acnt_prdt_cd_fno"]
        if "hts_id" in partial:
            row.hts_id = partial["hts_id"]
        if "base_url" in partial and partial["base_url"]:
            row.base_url = partial["base_url"]

        if sensitive_changed:
            row.validated_at = None  # 재검증 강제
        row.updated_at = now_kst_iso()
        self.db.flush()
        return self._row_to_dict(row)

    def delete_account(self, user_id: int, label: str) -> bool:
        """라벨로 계좌 삭제. default 계좌 삭제 시 다른 계좌 1개를 자동 default 승격."""
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        if not row:
            return False

        was_default = bool(row.is_default)
        self.db.delete(row)
        self.db.flush()

        if was_default:
            promote = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id)
                .order_by(UserKisCredentials.id.asc())
                .first()
            )
            if promote is not None:
                promote.is_default = True
                self.db.flush()
        return True

    def set_default(self, user_id: int, label: str) -> None:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        if not row:
            raise NotFoundError(f"라벨 '{label}' 의 계좌를 찾을 수 없습니다.")
        self._clear_other_defaults(user_id, except_row_id=row.id)
        row.is_default = True
        row.updated_at = now_kst_iso()
        self.db.flush()

    def mark_validated_label(self, user_id: int, label: str) -> None:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        if row:
            row.validated_at = now_kst_iso()
            self.db.flush()

    def is_valid_label(self, user_id: int, label: str) -> bool:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=label)
            .first()
        )
        if not row:
            return False
        return self._is_valid_row(row)

    # ── 백워드 호환 API (default 계좌 의미로 재정의) ──────────────

    def get(self, user_id: int) -> Optional[dict]:
        """plaintext dict 반환. default 계좌 우선, 미등록 시 None."""
        return self.get_default(user_id)

    def get_masked(self, user_id: int) -> Optional[dict]:
        """default 계좌의 마스킹 응답 (라우터 호환용)."""
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, is_default=True)
            .first()
        )
        if not row:
            row = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id)
                .order_by(UserKisCredentials.id.asc())
                .first()
            )
        return self._row_to_masked(row) if row else None

    def upsert(self, user_id: int, kis: dict) -> None:
        """등록/갱신 (기존 호출자 호환). 라벨 미지정 시 '기본' default 계좌로 동작.

        kis 키: app_key, app_secret, acnt_no, acnt_prdt_cd_stk,
                acnt_prdt_cd_fno?, hts_id?, base_url?, label?
        라벨 명시 시 해당 라벨 행 upsert. 미명시 시 default 행 upsert (없으면 '기본' 신규).
        """
        target_label = kis.get("label")
        if target_label is None:
            # default 행 찾기 → 없으면 '기본' 라벨로 신규.
            row = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id, is_default=True)
                .first()
            )
            if row is None:
                # 행 자체가 없으면 신규 — 첫 계좌는 자동 default.
                self.create_account(user_id, {**kis, "label": _DEFAULT_LABEL_FALLBACK})
                return
            target_label = row.label

        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, label=target_label)
            .first()
        )
        if row:
            # 기존 행 갱신
            row.app_key_enc = secure_store.encrypt(kis["app_key"])
            row.app_secret_enc = secure_store.encrypt(kis["app_secret"])
            row.acnt_no_enc = secure_store.encrypt(kis["acnt_no"])
            row.acnt_prdt_cd_stk = kis["acnt_prdt_cd_stk"]
            row.acnt_prdt_cd_fno = kis.get("acnt_prdt_cd_fno")
            row.hts_id = kis.get("hts_id")
            if kis.get("base_url"):
                row.base_url = kis["base_url"]
            row.validated_at = None  # 자격증명 변경 → 재검증 강제 (기존 정책 보존)
            row.updated_at = now_kst_iso()
            self.db.flush()
        else:
            self.create_account(user_id, {**kis, "label": target_label})

    def delete(self, user_id: int) -> bool:
        """default 계좌 1개 삭제 (백워드 호환). 다른 계좌가 자동 default 승격."""
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, is_default=True)
            .first()
        )
        if not row:
            # default 없으면 가장 오래된 행 삭제 (legacy 데이터 불변식 깨진 경우 방어).
            row = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id)
                .order_by(UserKisCredentials.id.asc())
                .first()
            )
        if not row:
            return False
        return self.delete_account(row.user_id, row.label)

    def mark_validated(self, user_id: int) -> None:
        """default 계좌 검증 (백워드 호환)."""
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, is_default=True)
            .first()
        )
        if row is None:
            row = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id)
                .order_by(UserKisCredentials.id.asc())
                .first()
            )
        if row:
            row.validated_at = now_kst_iso()
            self.db.flush()

    def is_valid(self, user_id: int) -> bool:
        row = (
            self.db.query(UserKisCredentials)
            .filter_by(user_id=user_id, is_default=True)
            .first()
        )
        if row is None:
            row = (
                self.db.query(UserKisCredentials)
                .filter_by(user_id=user_id)
                .order_by(UserKisCredentials.id.asc())
                .first()
            )
        if not row:
            return False
        return self._is_valid_row(row)

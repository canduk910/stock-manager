"""관리자 전용: 사용자 목록 조회/수정/삭제. Phase 4 단계 4."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from db.repositories.admin_repo import AdminRepository
from db.repositories.user_kis_repo import UserKisRepository
from db.repositories.user_repo import UserRepository
from db.session import get_session
from services.auth_deps import require_admin
from services.exceptions import ConflictError, NotFoundError

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


class PatchUserBody(BaseModel):
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    new_password: Optional[str] = Field(None, min_length=8)


@router.get("")
def list_users(
    q: Optional[str] = Query(None, description="username/name 부분 검색"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _admin: dict = Depends(require_admin),
):
    """사용자 목록 (검색 + 페이지네이션). has_kis 플래그 포함."""
    with get_session() as db:
        urepo = UserRepository(db)
        items = urepo.list_users(q=q, limit=limit, offset=offset)
        total = urepo.count_users(q=q)

        kis_repo = UserKisRepository(db)
        for item in items:
            item["has_kis"] = kis_repo.is_valid(item["id"])

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{user_id}")
def get_user(user_id: int, _admin: dict = Depends(require_admin)):
    """사용자 상세."""
    with get_session() as db:
        urepo = UserRepository(db)
        user = urepo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"user_id={user_id} 사용자를 찾을 수 없습니다.")
        user["has_kis"] = UserKisRepository(db).is_valid(user_id)
    return user


@router.patch("/{user_id}")
def patch_user(user_id: int, body: PatchUserBody, admin: dict = Depends(require_admin)):
    """역할 변경 또는 비밀번호 리셋. audit_log 기록."""
    if not body.role and not body.new_password:
        raise ConflictError("변경 항목이 없습니다 (role 또는 new_password 필요).")

    actor_id = admin["id"]
    changes: list[dict] = []

    with get_session() as db:
        urepo = UserRepository(db)
        target = urepo.get_by_id(user_id)
        if not target:
            raise NotFoundError(f"user_id={user_id} 사용자를 찾을 수 없습니다.")

        if body.role and body.role != target.get("role"):
            urepo.update_role(user_id, body.role)
            changes.append({"field": "role", "old": target.get("role"), "new": body.role})

        if body.new_password:
            from services.auth_service import _hash_password
            urepo.update_password(user_id, _hash_password(body.new_password))
            changes.append({"field": "password", "old": "***", "new": "***"})

        # audit log
        if changes:
            try:
                AdminRepository(db).add_audit_log(
                    actor_id=actor_id,
                    action="admin.users.patch",
                    target_type="user",
                    target_id=str(user_id),
                    new_value=changes,
                )
            except Exception:
                pass

    return {"updated": True, "changes": changes}


@router.delete("/{user_id}")
def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """사용자 삭제. 자기 자신 삭제 금지."""
    if user_id == admin["id"]:
        raise ConflictError("자기 자신을 삭제할 수 없습니다.")

    with get_session() as db:
        urepo = UserRepository(db)
        target = urepo.get_by_id(user_id)
        if not target:
            raise NotFoundError(f"user_id={user_id} 사용자를 찾을 수 없습니다.")
        urepo.delete_user(user_id)
        try:
            AdminRepository(db).add_audit_log(
                actor_id=admin["id"],
                action="admin.users.delete",
                target_type="user",
                target_id=str(user_id),
                old_value={"username": target.get("username")},
            )
        except Exception:
            pass

    return {"deleted": True}

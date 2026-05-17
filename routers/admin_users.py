"""관리자 전용: 사용자 목록 조회/수정/삭제. Phase 4 단계 4."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from db.repositories.admin_repo import AdminRepository
from db.repositories.page_view_repo import PageViewRepository
from db.repositories.user_kis_repo import UserKisRepository
from db.repositories.user_repo import UserRepository
from db.session import get_session
from db.utils import KST
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
    """사용자 목록 (검색 + 페이지네이션). has_kis + visit_count 포함.

    R4 (2026-05-04): visit_count는 PageViewRepository.count_by_user로 1쿼리(N+1 방지).
    """
    with get_session() as db:
        urepo = UserRepository(db)
        items = urepo.list_users(q=q, limit=limit, offset=offset)
        total = urepo.count_users(q=q)

        kis_repo = UserKisRepository(db)
        pv_repo = PageViewRepository(db)
        ids = [item["id"] for item in items]
        visits = pv_repo.count_by_user(ids)
        for item in items:
            item["has_kis"] = kis_repo.is_valid(item["id"])
            item["visit_count"] = visits.get(item["id"], 0)

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
        user["visit_count"] = PageViewRepository(db).count_by_user([user_id]).get(user_id, 0)
    return user


@router.get("/{user_id}/access-history")
def get_user_access_history(
    user_id: int,
    days: int = Query(30, ge=7, le=180, description="조회 일수 (7/30/90/180)"),
    top_paths: int = Query(5, ge=1, le=20, description="상위 N개 경로"),
    _admin: dict = Depends(require_admin),
):
    """사용자별 일별 접속 현황 + Top N 경로 + 마지막 접속.

    응답 shape:
      {
        user_id, username, name,
        last_seen_at: ISO|null,   # 전체 누계 기준
        total_views: int,         # 전체 누계 (days 무관, list_users.visit_count 정의 일치)
        days: int,
        daily: [{date, views, unique_paths}],  # KST 연속 시계열 (padding)
        top_paths: [{path, views}],            # days 범위 내 desc
      }
    """
    # KST 기준 날짜 범위 계산 (date_to=오늘, date_from=days-1일 전)
    now = datetime.now(KST)
    date_to = now.strftime("%Y-%m-%d")
    date_from = (now - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    with get_session() as db:
        urepo = UserRepository(db)
        user = urepo.get_by_id(user_id)
        if not user:
            raise NotFoundError(f"user_id={user_id} 사용자를 찾을 수 없습니다.")

        pv_repo = PageViewRepository(db)
        daily_rows = pv_repo.user_daily_timeseries(user_id, date_from, date_to)
        top_paths_rows = pv_repo.user_top_paths(user_id, date_from, date_to, top_paths)
        last_seen_at = pv_repo.user_last_seen_at(user_id)
        total_views = pv_repo.count_by_user([user_id]).get(user_id, 0)

    # 연속 시계열 padding: 데이터 없는 날 0 채움.
    daily_map = {r["date"]: r for r in daily_rows}
    daily: list[dict] = []
    start_date = datetime.strptime(date_from, "%Y-%m-%d").date()
    for offset in range(days):
        d = start_date + timedelta(days=offset)
        d_str = d.strftime("%Y-%m-%d")
        row = daily_map.get(d_str)
        if row:
            daily.append(row)
        else:
            daily.append({"date": d_str, "views": 0, "unique_paths": 0})

    return {
        "user_id": user_id,
        "username": user.get("username"),
        "name": user.get("name"),
        "last_seen_at": last_seen_at,
        "total_views": total_views,
        "days": days,
        "daily": daily,
        "top_paths": top_paths_rows,
    }


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

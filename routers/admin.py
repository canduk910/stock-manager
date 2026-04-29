"""Admin 관리 API 라우터 — AI 사용량, 한도, 감사 로그."""

import json
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.auth_deps import require_admin, get_current_user
from services.ai_gateway import get_ai_usage_status

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── AI 사용량 ─────────────────────────────────────────────────


@router.get("/ai-usage")
def get_ai_usage(
    date: Optional[str] = None,
    user_id: Optional[int] = None,
    _user: dict = Depends(require_admin),
):
    """유저별 AI 사용량 조회 (admin only)."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository
    from db.repositories.user_repo import UserRepository
    from services.ai_gateway import _today_kst

    target_date = date or _today_kst()
    with get_session() as db:
        repo = AdminRepository(db)
        user_repo = UserRepository(db)
        detail = repo.get_usage_detail(target_date, user_id)
        summary = repo.get_usage_summary(target_date)

        # 유저명 부착
        user_cache = {}
        for item in summary:
            uid = item["user_id"]
            if uid not in user_cache:
                u = user_repo.get_by_id(uid)
                user_cache[uid] = u.get("name", str(uid)) if u else str(uid)
            item["user_name"] = user_cache[uid]
            item["limit"] = repo.get_effective_limit(uid)

        return {"date": target_date, "summary": summary, "detail": detail}


@router.get("/ai-usage/me")
def get_my_ai_usage(_user: dict = Depends(get_current_user)):
    """내 AI 사용량 조회 (일반 유저용)."""
    return get_ai_usage_status(_user["id"])


# ── AI 한도 설정 ──────────────────────────────────────────────


class SetLimitBody(BaseModel):
    user_id: Optional[int] = None  # None이면 기본 한도
    daily_limit: int


@router.get("/ai-limits")
def get_ai_limits(_user: dict = Depends(require_admin)):
    """AI 호출 한도 설정 전체 조회."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository
    from db.repositories.user_repo import UserRepository

    with get_session() as db:
        repo = AdminRepository(db)
        user_repo = UserRepository(db)
        limits = repo.get_all_limits()

        for item in limits:
            if item["user_id"] is not None:
                u = user_repo.get_by_id(item["user_id"])
                item["user_name"] = u.get("name", str(item["user_id"])) if u else str(item["user_id"])
            else:
                item["user_name"] = "(기본 한도)"

        return {"limits": limits}


@router.put("/ai-limits")
def set_ai_limit(body: SetLimitBody, _user: dict = Depends(require_admin)):
    """AI 호출 한도 설정 (기본 또는 유저별)."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository

    actor_id = _user["id"]
    with get_session() as db:
        repo = AdminRepository(db)

        # 기존 값 기록 (감사 로그용)
        if body.user_id is not None:
            old = repo.get_user_limit(body.user_id)
        else:
            old = repo.get_default_limit()
        old_value = old["daily_limit"] if old else None

        result = repo.set_limit(body.user_id, body.daily_limit, actor_id)

        # 감사 로그
        repo.add_audit_log(
            actor_id=actor_id,
            action="set_ai_limit",
            target_type="ai_limit",
            target_id=str(body.user_id) if body.user_id else "default",
            old_value={"daily_limit": old_value},
            new_value={"daily_limit": body.daily_limit},
        )

        return result


@router.delete("/ai-limits/{user_id}")
def delete_user_limit(user_id: int, _user: dict = Depends(require_admin)):
    """유저별 개별 한도 삭제 (기본 한도로 복귀)."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository

    actor_id = _user["id"]
    with get_session() as db:
        repo = AdminRepository(db)
        old = repo.get_user_limit(user_id)
        deleted = repo.delete_user_limit(user_id)

        if deleted and old:
            repo.add_audit_log(
                actor_id=actor_id,
                action="delete_ai_limit",
                target_type="ai_limit",
                target_id=str(user_id),
                old_value={"daily_limit": old["daily_limit"]},
                new_value=None,
            )

        return {"deleted": deleted}


# ── 감사 로그 ─────────────────────────────────────────────────


@router.get("/audit-log")
def get_audit_log(
    limit: int = 100,
    offset: int = 0,
    _user: dict = Depends(require_admin),
):
    """감사 로그 이력 조회 (admin only)."""
    from db.session import get_session
    from db.repositories.admin_repo import AdminRepository
    from db.repositories.user_repo import UserRepository

    with get_session() as db:
        repo = AdminRepository(db)
        user_repo = UserRepository(db)
        result = repo.list_audit_logs(limit, offset)

        # 액터 이름 부착
        user_cache = {}
        for item in result["items"]:
            uid = item["actor_id"]
            if uid not in user_cache:
                u = user_repo.get_by_id(uid)
                user_cache[uid] = u.get("name", str(uid)) if u else str(uid)
            item["actor_name"] = user_cache[uid]

            # old_value, new_value JSON 파싱
            for field in ("old_value", "new_value"):
                if item[field]:
                    try:
                        item[field] = json.loads(item[field])
                    except (json.JSONDecodeError, TypeError):
                        pass

        return result

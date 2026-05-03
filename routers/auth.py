"""인증 API 라우터 — 회원가입/로그인/토큰갱신/비밀번호변경."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services import auth_service
from services.auth_deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterBody(BaseModel):
    username: str
    name: str
    password: str


class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str


@router.post("/register", status_code=201)
def register(body: RegisterBody):
    """회원가입. 첫 번째 가입자는 자동으로 admin."""
    user = auth_service.register(body.username, body.name, body.password)
    return {"user": user}


@router.post("/login")
def login(body: LoginBody):
    """로그인 → access_token + refresh_token."""
    return auth_service.login(body.username, body.password)


@router.post("/refresh")
def refresh(body: RefreshBody):
    """리프레시 토큰으로 새 access_token 발급."""
    return auth_service.refresh(body.refresh_token)


@router.post("/change-password")
def change_password(body: ChangePasswordBody, user: dict = Depends(get_current_user)):
    """비밀번호 변경 (로그인 필요)."""
    auth_service.change_password(user["id"], body.old_password, body.new_password)
    return {"ok": True}


@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    """현재 사용자 정보. Phase 4 D.4: has_kis 포함."""
    has_kis = False
    try:
        from db.session import get_session
        from db.repositories.user_kis_repo import UserKisRepository
        with get_session() as db:
            has_kis = UserKisRepository(db).is_valid(user["id"])
    except Exception:
        has_kis = False
    payload = dict(user)
    payload["has_kis"] = has_kis
    return {"user": payload}

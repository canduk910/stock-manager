"""인증 FastAPI 의존성 — get_current_user / require_admin / require_kis_user."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import get_user_by_id, verify_token
from services.exceptions import AuthenticationError, ConfigError, ForbiddenError

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """JWT Bearer 토큰에서 현재 사용자 추출. 실패 시 401.

    Phase 4 D.3: ContextVar에 user_id를 set하여 _kis_auth가 사용자별 KIS를 자동 선택.
    """
    if not credentials:
        raise AuthenticationError("인증 토큰이 필요합니다.")

    payload = verify_token(credentials.credentials, expected_type="access")
    user_id = int(payload["sub"])
    user = get_user_by_id(user_id)

    # Phase 4 D.3: ContextVar set — 동일 request 내 모든 KIS 호출이 사용자별로 격리됨.
    try:
        from routers._kis_auth import set_current_user_id
        set_current_user_id(user_id)
    except Exception:
        pass
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """admin 역할 필수. 실패 시 403."""
    if user.get("role") != "admin":
        raise ForbiddenError("관리자 권한이 필요합니다.")
    return user


def require_kis_user(user: dict = Depends(get_current_user)) -> dict:
    """사용자 KIS 자격증명 등록+검증 필수. 미등록 시 503.

    Phase 4 D.5: /portfolio, /order/*, /balance, /tax/* 라우트 보호용.
    """
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository
    with get_session() as db:
        repo = UserKisRepository(db)
        if not repo.is_valid(user["id"]):
            raise ConfigError(
                "사용자 KIS 자격증명이 등록/검증되지 않았습니다. /settings/kis 에서 등록하세요."
            )
    return user

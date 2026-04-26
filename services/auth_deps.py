"""인증 FastAPI 의존성 — get_current_user / require_admin."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import get_user_by_id, verify_token
from services.exceptions import AuthenticationError, ForbiddenError

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """JWT Bearer 토큰에서 현재 사용자 추출. 실패 시 401."""
    if not credentials:
        raise AuthenticationError("인증 토큰이 필요합니다.")

    payload = verify_token(credentials.credentials, expected_type="access")
    user_id = int(payload["sub"])
    return get_user_by_id(user_id)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """admin 역할 필수. 실패 시 403."""
    if user.get("role") != "admin":
        raise ForbiddenError("관리자 권한이 필요합니다.")
    return user

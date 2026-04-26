"""인증 서비스 — JWT 토큰 + 비밀번호 해싱 + 등록/로그인."""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from config import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET_KEY,
)
from db.repositories.user_repo import UserRepository
from db.session import get_session
from services.exceptions import AuthenticationError, ConflictError


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, expected_type: str = "access") -> dict:
    """JWT 토큰 검증. 반환: {"sub": user_id_str, "role": ..., "type": ...}."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise AuthenticationError("유효하지 않은 토큰입니다.")

    if payload.get("type") != expected_type:
        raise AuthenticationError("토큰 유형이 올바르지 않습니다.")

    return payload


def register(username: str, name: str, password: str) -> dict:
    """사용자 등록. 첫 번째 가입자는 admin."""
    if len(password) < 4:
        raise AuthenticationError("비밀번호는 4자 이상이어야 합니다.")

    with get_session() as db:
        repo = UserRepository(db)

        if repo.get_by_username(username):
            raise ConflictError(f"이미 존재하는 아이디입니다: {username}")

        role = "admin" if repo.count() == 0 else "user"
        hashed = _hash_password(password)
        user = repo.create_user(username, name, hashed, role)

    return user


def login(username: str, password: str) -> dict:
    """로그인. 반환: {access_token, refresh_token, user}."""
    with get_session() as db:
        repo = UserRepository(db)
        user = repo.get_by_username(username)

    if not user or not _verify_password(password, user["hashed_password"]):
        raise AuthenticationError("아이디 또는 비밀번호가 올바르지 않습니다.")

    user_safe = {k: v for k, v in user.items() if k != "hashed_password"}
    access_token = create_access_token(user["id"], user["role"])
    refresh_token = create_refresh_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_safe,
    }


def refresh(refresh_token_str: str) -> dict:
    """리프레시 토큰으로 새 access_token 발급."""
    payload = verify_token(refresh_token_str, expected_type="refresh")
    user_id = int(payload["sub"])

    with get_session() as db:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)

    if not user:
        raise AuthenticationError("유효하지 않은 사용자입니다.")

    access_token = create_access_token(user["id"], user["role"])
    return {"access_token": access_token, "token_type": "bearer"}


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """비밀번호 변경."""
    if len(new_password) < 4:
        raise AuthenticationError("새 비밀번호는 4자 이상이어야 합니다.")

    with get_session() as db:
        repo = UserRepository(db)
        from db.models.user import User
        row = db.query(User).filter_by(id=user_id).first()
        if not row:
            raise AuthenticationError("사용자를 찾을 수 없습니다.")

        if not _verify_password(old_password, row.hashed_password):
            raise AuthenticationError("현재 비밀번호가 올바르지 않습니다.")

        hashed = _hash_password(new_password)
        repo.update_password(user_id, hashed)

    return True


def get_user_by_id(user_id: int) -> dict:
    """사용자 정보 조회 (비밀번호 제외)."""
    with get_session() as db:
        repo = UserRepository(db)
        user = repo.get_by_id(user_id)
    if not user:
        raise AuthenticationError("사용자를 찾을 수 없습니다.")
    return user

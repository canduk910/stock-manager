"""사용자 본인 KIS 자격증명 등록/조회/삭제/재검증 API.

`POST /api/me/kis` — 등록 + 즉시 검증
`GET  /api/me/kis` — 마스킹된 상태 조회
`DELETE /api/me/kis` — 삭제 + 토큰 캐시 invalidate
`POST /api/me/kis/validate` — 재검증

Phase 4 D.4. 모든 응답에서 app_secret/acnt_no는 미노출, app_key는 끝 4자리만 노출.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from db.repositories.user_kis_repo import UserKisRepository
from db.session import get_session
from routers._kis_auth import clear_token_cache
from services import kis_validator
from services.auth_deps import get_current_user
from services.exceptions import NotFoundError

router = APIRouter(prefix="/api/me/kis", tags=["me-kis"])


class KisRegisterBody(BaseModel):
    app_key: str = Field(..., min_length=8)
    app_secret: str = Field(..., min_length=8)
    acnt_no: str = Field(..., min_length=4)
    acnt_prdt_cd_stk: str = Field(..., min_length=2, max_length=2)
    acnt_prdt_cd_fno: Optional[str] = Field(None, min_length=2, max_length=2)
    hts_id: Optional[str] = None
    base_url: Optional[str] = None


def _user_id(user: dict) -> int:
    return int(user["id"])


@router.post("")
def register_kis(body: KisRegisterBody, user: dict = Depends(get_current_user)):
    """KIS 자격증명 등록 + 즉시 검증.

    1) /oauth2/tokenP 호출로 키 유효성 확인
    2) 성공 시 user_kis_credentials에 upsert + mark_validated
    실패 시 ExternalAPIError(502).
    """
    # 1) 검증 먼저 — 실패 시 ExternalAPIError raise
    kis_validator.validate_kis(body.app_key, body.app_secret, body.base_url)

    # 2) 저장 + 검증 시각 기록
    uid = _user_id(user)
    payload = body.model_dump()
    with get_session() as db:
        repo = UserKisRepository(db)
        repo.upsert(uid, payload)
        repo.mark_validated(uid)

    # 3) 토큰 캐시 invalidate (이전 사용자 토큰 잔존 방지)
    clear_token_cache(uid)

    # 4) 마스킹된 상태 반환
    with get_session() as db:
        return UserKisRepository(db).get_masked(uid)


@router.get("")
def get_kis(user: dict = Depends(get_current_user)):
    """현재 등록된 KIS 자격증명 조회 (마스킹). 미등록 시 None 반환 + 200."""
    uid = _user_id(user)
    with get_session() as db:
        masked = UserKisRepository(db).get_masked(uid)
    if not masked:
        return {"registered": False, "is_active": False}
    masked["registered"] = True
    return masked


@router.delete("")
def delete_kis(user: dict = Depends(get_current_user)):
    """KIS 자격증명 삭제 + 토큰 캐시 invalidate."""
    uid = _user_id(user)
    with get_session() as db:
        ok = UserKisRepository(db).delete(uid)
    if not ok:
        raise NotFoundError("등록된 KIS 자격증명이 없습니다.")
    clear_token_cache(uid)
    return {"deleted": True}


@router.post("/validate")
def validate_kis_endpoint(user: dict = Depends(get_current_user)):
    """기존 등록된 KIS 자격증명 재검증."""
    uid = _user_id(user)
    with get_session() as db:
        repo = UserKisRepository(db)
        creds = repo.get(uid)
    if not creds:
        raise NotFoundError("등록된 KIS 자격증명이 없습니다.")

    kis_validator.validate_kis(creds["app_key"], creds["app_secret"], creds.get("base_url"))

    with get_session() as db:
        repo = UserKisRepository(db)
        repo.mark_validated(uid)
        return repo.get_masked(uid)

"""사용자 본인 KIS 자격증명 멀티 계좌 CRUD API.

R3 (KIS 멀티 계좌, 2026-05-15) — 단일 row 가정 폐기 + 라벨 기반 6 라우트:

`POST   /api/me/kis`              — 계좌 등록 + 즉시 검증 (라벨 중복 시 409)
`GET    /api/me/kis`              — 전체 계좌 목록 (마스킹) + 백워드 호환 메타
`GET    /api/me/kis/{label}`      — 단일 계좌 마스킹 응답
`PUT    /api/me/kis/{label}`      — 라벨 변경 또는 자격증명 갱신 (자격증명 변경 시 자동 재검증)
`DELETE /api/me/kis/{label}`      — 계좌 삭제 (default 삭제 시 자동 승격)
`POST   /api/me/kis/{label}/default`  — is_default 전환
`POST   /api/me/kis/{label}/validate` — 재검증 (24h TTL 갱신)

기존 1계좌 라우트(`POST /api/me/kis`, `GET /api/me/kis`, `DELETE /api/me/kis`,
`POST /api/me/kis/validate`)도 백워드 호환을 위해 보존된다:
- POST: 라벨 미지정 시 '기본' 라벨로 등록.
- GET: accounts 배열 + default 계좌 메타(`registered`/`is_active`/`app_key_masked`) 동시 반환.
- DELETE: default 계좌 삭제 (다른 계좌 자동 승격).
- /validate: default 계좌 재검증.

모든 응답에서 app_secret/acnt_no 미노출. app_key 끝 4자리, acnt_no 앞2/뒤2만 노출.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from db.repositories.user_kis_repo import UserKisRepository
from db.session import get_session
from routers._kis_auth import clear_token_cache
from services import account_label_matcher, kis_validator
from services.auth_deps import get_current_user
from services.exceptions import NotFoundError, ServiceError

router = APIRouter(prefix="/api/me/kis", tags=["me-kis"])


class KisRegisterBody(BaseModel):
    """POST 등록 body — label 옵셔널(미지정 시 '기본')."""
    label: Optional[str] = Field(None, max_length=50)
    is_default: Optional[bool] = None
    app_key: str = Field(..., min_length=8)
    app_secret: str = Field(..., min_length=8)
    acnt_no: str = Field(..., min_length=4)
    acnt_prdt_cd_stk: str = Field(..., min_length=2, max_length=2)
    acnt_prdt_cd_fno: Optional[str] = Field(None, min_length=2, max_length=2)
    hts_id: Optional[str] = None
    base_url: Optional[str] = None


class KisUpdateBody(BaseModel):
    """PUT 갱신 body — 모든 필드 옵셔널 (부분 갱신)."""
    label: Optional[str] = Field(None, max_length=50)
    app_key: Optional[str] = Field(None, min_length=8)
    app_secret: Optional[str] = Field(None, min_length=8)
    acnt_no: Optional[str] = Field(None, min_length=4)
    acnt_prdt_cd_stk: Optional[str] = Field(None, min_length=2, max_length=2)
    acnt_prdt_cd_fno: Optional[str] = Field(None, min_length=2, max_length=2)
    hts_id: Optional[str] = None
    base_url: Optional[str] = None


def _user_id(user: dict) -> int:
    return int(user["id"])


def _summary_for_default(default_account: Optional[dict]) -> dict:
    """default 계좌의 마스킹 응답을 백워드 호환 형태로 변환."""
    if default_account is None:
        return {"registered": False, "is_active": False}
    return {
        **default_account,
        "registered": True,
        "is_active": default_account.get("is_active", False),
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/me/kis — 계좌 등록
# ──────────────────────────────────────────────────────────────────────────────


@router.post("")
def register_kis(body: KisRegisterBody, user: dict = Depends(get_current_user)):
    """KIS 자격증명 등록 + 즉시 검증.

    1) /oauth2/tokenP 호출로 키 유효성 확인
    2) 성공 시 user_kis_credentials 에 신규 row 삽입 + mark_validated
    실패 시 ExternalAPIError(502). 라벨 중복 시 ConflictError(409).
    첫 계좌는 무조건 is_default=true.
    """
    # 1) 검증 먼저 — 실패 시 ExternalAPIError raise
    kis_validator.validate_kis(body.app_key, body.app_secret, body.base_url)

    # 2) 저장 + 검증 시각 기록
    uid = _user_id(user)
    payload = body.model_dump(exclude_none=False)
    label = payload.get("label") or "기본"
    payload["label"] = label

    with get_session() as db:
        repo = UserKisRepository(db)
        # create_account 가 라벨 중복 시 ConflictError raise → 409 자동 변환.
        repo.create_account(uid, payload)
        repo.mark_validated_label(uid, label)

    # 3) 토큰 캐시 invalidate (해당 user_id 전체 — 어차피 캐시 미스로 재발급)
    clear_token_cache(uid); account_label_matcher.invalidate_cache(uid)

    with get_session() as db:
        masked = UserKisRepository(db).get_masked_by_label(uid, label)
    return masked


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/me/kis — 전체 목록 + 백워드 호환 메타
# ──────────────────────────────────────────────────────────────────────────────


@router.get("")
def get_kis(user: dict = Depends(get_current_user)):
    """등록된 모든 KIS 계좌 (마스킹) + 백워드 호환 default 메타.

    응답 shape:
    {
      "accounts": [{label, is_default, app_key_masked, acnt_no_masked, ...}, ...],
      "default_label": "주식" | None,
      # 백워드 호환 (default 계좌 정보 — 기존 단일-row 응답 호환)
      "registered": bool,
      "is_active": bool,
      "app_key_masked": str | None,
      ...
    }
    """
    uid = _user_id(user)
    with get_session() as db:
        repo = UserKisRepository(db)
        accounts = repo.list_accounts_masked(uid)

    default_label = None
    default_account = None
    for a in accounts:
        if a.get("is_default"):
            default_label = a["label"]
            default_account = a
            break
    # default 부재 시 첫 계좌(가장 오래된) 폴백 — UI 가 항상 1개를 표시할 수 있도록.
    if default_account is None and accounts:
        default_account = accounts[0]
        default_label = default_account["label"]

    summary = _summary_for_default(default_account)
    return {
        "accounts": accounts,
        "default_label": default_label,
        **summary,
    }


# ──────────────────────────────────────────────────────────────────────────────
# GET /api/me/kis/{label}
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/{label}")
def get_kis_by_label(label: str, user: dict = Depends(get_current_user)):
    uid = _user_id(user)
    with get_session() as db:
        masked = UserKisRepository(db).get_masked_by_label(uid, label)
    if not masked:
        raise NotFoundError(f"라벨 '{label}' 의 계좌를 찾을 수 없습니다.")
    return masked


# ──────────────────────────────────────────────────────────────────────────────
# PUT /api/me/kis/{label} — 라벨 변경 + 자격증명 갱신
# ──────────────────────────────────────────────────────────────────────────────


@router.put("/{label}")
def update_kis(label: str, body: KisUpdateBody, user: dict = Depends(get_current_user)):
    """기존 계좌 갱신. 자격증명 변경 시 자동 재검증.

    - label 변경 + 자격증명 동시 변경 가능.
    - 라벨 중복 시 409 ConflictError.
    - 라벨 없음 404 NotFoundError.
    - 자격증명 변경 후 KIS 검증 실패 시 502 ExternalAPIError (변경 자체는 롤백되지 않음 — 클라이언트가 재시도).
    """
    uid = _user_id(user)
    partial = body.model_dump(exclude_none=True)
    sensitive_changed = any(k in partial for k in ("app_key", "app_secret", "acnt_no", "base_url"))

    with get_session() as db:
        repo = UserKisRepository(db)
        updated = repo.update_account(uid, label, partial)

    target_label = partial.get("label") or label

    # 자격증명 변경 시 재검증 (실패 시 502 raise; 행은 이미 저장되었으므로 마지막 검증만 갱신 X)
    if sensitive_changed:
        # 최신 자격증명 평문 재조회 (validator 에 평문 필요)
        with get_session() as db:
            current = UserKisRepository(db).get_by_label(uid, target_label)
        kis_validator.validate_kis(
            current["app_key"], current["app_secret"], current.get("base_url"),
        )
        with get_session() as db:
            UserKisRepository(db).mark_validated_label(uid, target_label)

    # 토큰 캐시 invalidate
    clear_token_cache(uid); account_label_matcher.invalidate_cache(uid)

    with get_session() as db:
        return UserKisRepository(db).get_masked_by_label(uid, target_label)


# ──────────────────────────────────────────────────────────────────────────────
# DELETE /api/me/kis/{label}
# ──────────────────────────────────────────────────────────────────────────────


@router.delete("/{label}")
def delete_kis_by_label(label: str, user: dict = Depends(get_current_user)):
    uid = _user_id(user)
    with get_session() as db:
        ok = UserKisRepository(db).delete_account(uid, label)
    if not ok:
        raise NotFoundError(f"라벨 '{label}' 의 계좌를 찾을 수 없습니다.")
    clear_token_cache(uid); account_label_matcher.invalidate_cache(uid)
    return {"deleted": True, "label": label}


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/me/kis/{label}/default — is_default 전환
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/{label}/default")
def set_default_kis(label: str, user: dict = Depends(get_current_user)):
    uid = _user_id(user)
    with get_session() as db:
        repo = UserKisRepository(db)
        repo.set_default(uid, label)
        return repo.get_masked_by_label(uid, label)


# ──────────────────────────────────────────────────────────────────────────────
# POST /api/me/kis/{label}/validate — 재검증
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/{label}/validate")
def validate_kis_by_label(label: str, user: dict = Depends(get_current_user)):
    uid = _user_id(user)
    with get_session() as db:
        repo = UserKisRepository(db)
        creds = repo.get_by_label(uid, label)
    if not creds:
        raise NotFoundError(f"라벨 '{label}' 의 계좌를 찾을 수 없습니다.")

    kis_validator.validate_kis(creds["app_key"], creds["app_secret"], creds.get("base_url"))

    with get_session() as db:
        repo = UserKisRepository(db)
        repo.mark_validated_label(uid, label)
        return repo.get_masked_by_label(uid, label)


# ──────────────────────────────────────────────────────────────────────────────
# 백워드 호환 단일-row 라우트 (기존 클라이언트 호환)
# ──────────────────────────────────────────────────────────────────────────────


@router.delete("")
def delete_kis_default(user: dict = Depends(get_current_user)):
    """기존 1계좌 DELETE — default 계좌 삭제 + 자동 승격."""
    uid = _user_id(user)
    with get_session() as db:
        repo = UserKisRepository(db)
        default = repo.get_default(uid)
        if not default:
            raise NotFoundError("등록된 KIS 자격증명이 없습니다.")
        ok = repo.delete_account(uid, default["label"])
    if not ok:
        raise NotFoundError("등록된 KIS 자격증명이 없습니다.")
    clear_token_cache(uid); account_label_matcher.invalidate_cache(uid)
    return {"deleted": True}


@router.post("/validate")
def validate_kis_default(user: dict = Depends(get_current_user)):
    """기존 단일-row /validate — default 계좌 재검증."""
    uid = _user_id(user)
    with get_session() as db:
        repo = UserKisRepository(db)
        default = repo.get_default(uid)
    if not default:
        raise NotFoundError("등록된 KIS 자격증명이 없습니다.")

    kis_validator.validate_kis(default["app_key"], default["app_secret"], default.get("base_url"))

    with get_session() as db:
        repo = UserKisRepository(db)
        repo.mark_validated_label(uid, default["label"])
        return repo.get_masked_by_label(uid, default["label"])

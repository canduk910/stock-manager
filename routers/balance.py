"""잔고 조회 API 라우터.

R4 (KIS 멀티 계좌, 2026-05-15): 합산/단독 모드 지원.

- `GET /api/balance` — 운영자 .env 키 (백워드 호환). 등록 사용자 미지정.
- `GET /api/balance?account_label=주식` — 사용자의 특정 계좌 단독.
- `GET /api/balance` (user 로그인 + account_label 미지정) — 사용자의 모든 등록 계좌 합산.

KIS 조회 / 합산 로직은 모두 `services/balance_service.py` 위임. 라우터는 의존성 + 응답 변환만.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from routers._kis_auth import (
    set_current_account_label,
    set_current_user_id,
)
from services import balance_service
from services.auth_deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["balance"])


@router.get("/balance")
def get_balance(
    account_label: Optional[str] = Query(None, description="계좌 라벨 (생략 시 사용자 모든 계좌 합산)"),
    user: dict = Depends(require_admin),
):
    """잔고 조회 — 멀티 계좌 합산 또는 단독 모드.

    REQ-API-02:
    - `account_label=None` → 사용자의 모든 등록 계좌 병렬 조회 후 합산.
    - `account_label=str` → 해당 라벨 계좌 단독 조회 (동일 합산 shape 반환).
    - 등록 0개 + account_label=None → 200 + 빈 응답 (raise 금지).
    - `accounts: [{label, is_default, acnt_no_masked, fno_enabled}]` 메타 포함.
    - `fno_enabled` = 계좌 중 1개라도 활성이면 True (REQ-BALANCE-04).
    - `partial_failure` 메타 — 부분 실패 계좌 안내 (REQ-BALANCE-03).
    """
    user_id = int(user["id"]) if user and user.get("id") else None
    # ContextVar 전파 (서비스 체인이 직접 인자 없이도 라벨 인지)
    set_current_user_id(user_id)
    set_current_account_label(account_label)

    return balance_service.fetch_aggregated_balance(user_id, account_label)

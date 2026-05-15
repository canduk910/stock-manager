"""KIS API 인증 공통 모듈.

토큰 발급/캐싱, hashkey 발급, 계좌 정보 헬퍼.
balance.py, order.py 등에서 공용으로 사용한다.

Phase 4 (D.2): 사용자별 KIS 자격증명 분기.
R2 (KIS 멀티 계좌, 2026-05-15): 사용자 내 계좌 라벨별 분기.
- user_id=None → 시스템 호출(시세/market_board 등) → 운영자 .env 키 fallback
- user_id=int, account_label=None → 사용자 default 계좌
- user_id=int, account_label='주식' → 특정 라벨 계좌
- 미등록/검증만료 시 ConfigError(503), 라벨 없으면 NotFoundError(404)

토큰 캐시는 `(user_id, account_label)` 튜플 키로 격리.
"""

from __future__ import annotations

import json
import time
from contextvars import ContextVar
from typing import Optional

import requests

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK, KIS_ACNT_PRDT_CD_FNO, KIS_BASE_URL
from services.exceptions import ConfigError, ExternalAPIError, NotFoundError

# 라우터 진입 시 set, 서비스 내부 호출 체인 전반에서 자동 참조.
# explicit 인자가 우선; ContextVar는 fallback.
_current_user_id: ContextVar[Optional[int]] = ContextVar("kis_user_id", default=None)
_current_account_label: ContextVar[Optional[str]] = ContextVar("kis_account_label", default=None)


def set_current_user_id(user_id: Optional[int]) -> None:
    """라우터에서 호출 (Depends 주입 후). FastAPI Depends에서 set 하면 동일 request 내 모든 KIS 호출이 사용자별로 격리된다."""
    _current_user_id.set(user_id)


def get_current_user_id() -> Optional[int]:
    return _current_user_id.get()


def set_current_account_label(label: Optional[str]) -> None:
    """라우터에서 호출. 요청 단위 라벨 전파(REQ-AUTH-03).

    동일 request 내 모든 KIS 호출이 해당 라벨 계좌로 격리된다.
    explicit account_label 인자가 우선; ContextVar 는 fallback.
    """
    _current_account_label.set(label)


def get_current_account_label() -> Optional[str]:
    return _current_account_label.get()


def _resolve_user_id(explicit: Optional[int]) -> Optional[int]:
    """explicit 가 명시적으로 주어졌으면 그것을 우선, 아니면 ContextVar."""
    if explicit is not None:
        return explicit
    return _current_user_id.get()


def _resolve_account_label(explicit: Optional[str]) -> Optional[str]:
    """explicit 가 명시적으로 주어졌으면 그것을 우선, 아니면 ContextVar.

    None 으로 명시 호출 + ContextVar=None 이면 default 계좌 분기.
    """
    if explicit is not None:
        return explicit
    return _current_account_label.get()

# 운영자 기본 BASE_URL (시스템 호출 + 사용자별 KIS는 자기 base_url 사용)
BASE_URL = KIS_BASE_URL

# (user_id, account_label) 별 토큰 캐시. (None, None)=운영자 키(시스템 호출용).
# account_label=None 은 default 계좌를 의미 — Repository 에서 default 행을 찾아 매핑.
_token_cache: dict[tuple[Optional[int], Optional[str]], tuple[str, float]] = {}


def get_kis_credentials(
    user_id: Optional[int] = None,
    account_label: Optional[str] = None,
) -> tuple[str, str, str, str, str]:
    """KIS 자격증명을 반환한다. 누락 시 ConfigError(503), 라벨 부재 시 NotFoundError(404).

    Args:
        user_id: None=ContextVar→.env 폴백 / int=DB 조회
        account_label: None=default 계좌 / str=특정 라벨

    Returns:
        (app_key, app_secret, acnt_no, acnt_prdt_cd_stk, acnt_prdt_cd_fno)
    """
    user_id = _resolve_user_id(user_id)
    account_label = _resolve_account_label(account_label)

    if user_id is None:
        # 운영자 .env 키 (account_label 무시)
        if not all([KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK]):
            missing = [
                name for name, val in [
                    ("KIS_APP_KEY", KIS_APP_KEY),
                    ("KIS_APP_SECRET", KIS_APP_SECRET),
                    ("KIS_ACNT_NO", KIS_ACNT_NO),
                    ("KIS_ACNT_PRDT_CD_STK", KIS_ACNT_PRDT_CD_STK),
                ] if not val
            ]
            raise ConfigError(f"KIS API 키가 설정되지 않았습니다. 누락된 환경변수: {', '.join(missing)}")
        return KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK, KIS_ACNT_PRDT_CD_FNO

    # 사용자별 KIS — DB 에서 복호화
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository

    with get_session() as db:
        repo = UserKisRepository(db)
        if account_label is None:
            creds = repo.get_default(user_id)
            if not creds:
                raise ConfigError(
                    "사용자 KIS 자격증명이 등록되지 않았습니다. /settings/kis 에서 등록하세요."
                )
        else:
            creds = repo.get_by_label(user_id, account_label)
            if not creds:
                raise NotFoundError(f"라벨 '{account_label}' 의 KIS 계좌를 찾을 수 없습니다.")

    return (
        creds["app_key"],
        creds["app_secret"],
        creds["acnt_no"],
        creds["acnt_prdt_cd_stk"],
        creds.get("acnt_prdt_cd_fno") or "",
    )


def _get_user_base_url(user_id: Optional[int], account_label: Optional[str] = None) -> str:
    """사용자별 계좌별 base_url 또는 운영자 기본값."""
    user_id = _resolve_user_id(user_id)
    account_label = _resolve_account_label(account_label)
    if user_id is None:
        return BASE_URL
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository
    with get_session() as db:
        repo = UserKisRepository(db)
        if account_label is None:
            creds = repo.get_default(user_id)
        else:
            creds = repo.get_by_label(user_id, account_label)
    if creds and creds.get("base_url"):
        return creds["base_url"]
    return BASE_URL


def get_access_token(
    user_id: Optional[int] = None,
    account_label: Optional[str] = None,
) -> str:
    """OAuth2 토큰을 발급/캐싱하여 반환한다.

    (user_id, account_label) 별 캐시 키 분리. TTL(만료 60초 전) 자동 재발급.
    """
    user_id = _resolve_user_id(user_id)
    account_label = _resolve_account_label(account_label)
    cache_key = (user_id, account_label)

    now = time.time()
    cached = _token_cache.get(cache_key)
    if cached and now < cached[1]:
        return cached[0]

    app_key, app_secret, _, _, _ = get_kis_credentials(user_id, account_label)
    base_url = _get_user_base_url(user_id, account_label)

    url = f"{base_url}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body), timeout=10)
    except requests.RequestException as e:
        raise ExternalAPIError(f"KIS 토큰 발급 요청 실패: {e}")

    if res.status_code != 200:
        raise ExternalAPIError(f"KIS 토큰 발급 실패: {res.text}")

    data = res.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 86400))
    _token_cache[cache_key] = (token, now + expires_in - 60)
    return token


def get_access_token_safe(
    user_id: Optional[int] = None,
    account_label: Optional[str] = None,
) -> Optional[str]:
    """토큰 반환. 키 미설정 또는 발급 실패 시 None (예외 없음)."""
    try:
        return get_access_token(user_id, account_label)
    except Exception:
        return None


def clear_token_cache(
    user_id: Optional[int] = "__ALL__",
    account_label: Optional[str] = "__ALL__",
) -> None:
    """토큰 캐시 초기화.

    user_id="__ALL__" (기본) → 전체 초기화.
    user_id=None → 운영자 키 토큰만 초기화.
    user_id=int → 해당 사용자 토큰만 초기화 (account_label='__ALL__' 이면 모든 라벨).
    user_id=int + account_label='X' → 해당 (user_id, 'X') 만 초기화.
    """
    global _token_cache
    if user_id == "__ALL__":
        _token_cache = {}
        return
    if account_label == "__ALL__":
        # 해당 user_id 의 모든 라벨 토큰 제거.
        _token_cache = {k: v for k, v in _token_cache.items() if k[0] != user_id}
        return
    _token_cache.pop((user_id, account_label), None)


def issue_hashkey(
    data: dict,
    user_id: Optional[int] = None,
    account_label: Optional[str] = None,
) -> str:
    """POST 요청 데이터에 대한 hashkey를 발급한다."""
    app_key, app_secret, _, _, _ = get_kis_credentials(user_id, account_label)
    base_url = _get_user_base_url(user_id, account_label)
    url = f"{base_url}/uapi/hashkey"
    headers = {
        "content-type": "application/json",
        "appKey": app_key,
        "appSecret": app_secret,
        "User-Agent": "Mozilla/5.0",
    }
    resp = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
    return resp.json()["HASH"]


def make_headers(token: str, app_key: str, app_secret: str, tr_id: str, *, hashkey: str = None) -> dict:
    """KIS API 공통 헤더를 생성한다."""
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": app_key,
        "appsecret": app_secret,
        "tr_id": tr_id,
        "custtype": "P",
    }
    if hashkey:
        headers["hashkey"] = hashkey
    return headers

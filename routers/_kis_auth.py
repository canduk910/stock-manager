"""KIS API 인증 공통 모듈.

토큰 발급/캐싱, hashkey 발급, 계좌 정보 헬퍼.
balance.py, order.py 등에서 공용으로 사용한다.

Phase 4 (D.2): 사용자별 KIS 자격증명 분기.
- user_id=None → 시스템 호출(시세/market_board 등) → 운영자 .env 키 fallback
- user_id=int → user_kis_repo에서 복호화한 사용자 KIS 사용 (미등록/검증만료 시 ConfigError 503)

토큰 캐시는 user_id별 분리(_token_cache: dict). 멀티 인스턴스 확장 시 노드별 캐시는 격리됨
(F-4 메모: Redis 등 외부 토큰 풀 도입 전까지는 인스턴스 수만큼 토큰 발급).
"""

from __future__ import annotations

import json
import time
from contextvars import ContextVar
from typing import Optional

import requests

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK, KIS_ACNT_PRDT_CD_FNO, KIS_BASE_URL
from services.exceptions import ConfigError, ExternalAPIError

# 라우터 진입 시 set, 서비스 내부 호출 체인 전반에서 자동 참조.
# explicit user_id 인자가 우선; ContextVar는 fallback.
_current_user_id: ContextVar[Optional[int]] = ContextVar("kis_user_id", default=None)


def set_current_user_id(user_id: Optional[int]) -> None:
    """라우터에서 호출 (Depends 주입 후). FastAPI Depends에서 set 하면 동일 request 내 모든 KIS 호출이 사용자별로 격리된다."""
    _current_user_id.set(user_id)


def get_current_user_id() -> Optional[int]:
    return _current_user_id.get()


def _resolve_user_id(explicit: Optional[int]) -> Optional[int]:
    """explicit가 명시적으로 주어졌으면 그것을 우선, 아니면 ContextVar."""
    if explicit is not None:
        return explicit
    return _current_user_id.get()

# 운영자 기본 BASE_URL (시스템 호출 + 사용자별 KIS는 자기 base_url 사용)
BASE_URL = KIS_BASE_URL

# user_id별 토큰 캐시. None=운영자 키(시스템 호출용).
_token_cache: dict[Optional[int], tuple[str, float]] = {}


def get_kis_credentials(user_id: Optional[int] = None) -> tuple[str, str, str, str, str]:
    """KIS 자격증명을 반환한다. 누락 시 ConfigError(503).

    Args:
        user_id: None이면 ContextVar에서 조회 (라우터에서 set_current_user_id() 호출 필요).
                 ContextVar도 None이면 운영자 .env 키 (시스템 호출 한정).
                 int이면 user_kis_repo에서 복호화한 사용자 KIS.

    Returns:
        (app_key, app_secret, acnt_no, acnt_prdt_cd_stk, acnt_prdt_cd_fno)
        acnt_prdt_cd_fno는 선택 — 미설정 시 빈 문자열.
    """
    user_id = _resolve_user_id(user_id)
    if user_id is None:
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

    # 사용자별 KIS — DB에서 복호화
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository

    with get_session() as db:
        repo = UserKisRepository(db)
        creds = repo.get(user_id)

    if not creds:
        raise ConfigError(
            "사용자 KIS 자격증명이 등록되지 않았습니다. /settings/kis 에서 등록하세요."
        )
    return (
        creds["app_key"],
        creds["app_secret"],
        creds["acnt_no"],
        creds["acnt_prdt_cd_stk"],
        creds.get("acnt_prdt_cd_fno") or "",
    )


def _get_user_base_url(user_id: Optional[int]) -> str:
    """사용자별 base_url 또는 운영자 기본값."""
    user_id = _resolve_user_id(user_id)
    if user_id is None:
        return BASE_URL
    from db.session import get_session
    from db.repositories.user_kis_repo import UserKisRepository
    with get_session() as db:
        repo = UserKisRepository(db)
        creds = repo.get(user_id)
    if creds and creds.get("base_url"):
        return creds["base_url"]
    return BASE_URL


def get_access_token(user_id: Optional[int] = None) -> str:
    """OAuth2 토큰을 발급/캐싱하여 반환한다.

    user_id별 캐시 키 분리. TTL(만료 60초 전) 자동 재발급.
    """
    user_id = _resolve_user_id(user_id)
    now = time.time()
    cached = _token_cache.get(user_id)
    if cached and now < cached[1]:
        return cached[0]

    app_key, app_secret, _, _, _ = get_kis_credentials(user_id)
    base_url = _get_user_base_url(user_id)

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
    _token_cache[user_id] = (token, now + expires_in - 60)
    return token


def get_access_token_safe(user_id: Optional[int] = None) -> Optional[str]:
    """토큰 반환. 키 미설정 또는 발급 실패 시 None (예외 없음)."""
    try:
        return get_access_token(user_id)
    except Exception:
        return None


def clear_token_cache(user_id: Optional[int] = "__ALL__") -> None:
    """토큰 캐시 초기화.

    user_id="__ALL__"(기본) → 전체 초기화.
    user_id=None → 운영자 키 토큰만 초기화.
    user_id=int → 해당 사용자 토큰만 초기화.
    """
    global _token_cache
    if user_id == "__ALL__":
        _token_cache = {}
    else:
        _token_cache.pop(user_id, None)


def issue_hashkey(data: dict, user_id: Optional[int] = None) -> str:
    """POST 요청 데이터에 대한 hashkey를 발급한다."""
    app_key, app_secret, _, _, _ = get_kis_credentials(user_id)
    base_url = _get_user_base_url(user_id)
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

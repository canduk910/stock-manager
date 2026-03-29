"""KIS API 인증 공통 모듈.

토큰 발급/캐싱, hashkey 발급, 계좌 정보 헬퍼.
balance.py, order.py 등에서 공용으로 사용한다.
"""

import json

import requests

from config import KIS_APP_KEY, KIS_APP_SECRET, KIS_ACNT_NO, KIS_ACNT_PRDT_CD_STK, KIS_ACNT_PRDT_CD_FNO, KIS_BASE_URL
from services.exceptions import ConfigError, ExternalAPIError

BASE_URL = KIS_BASE_URL

# 인메모리 토큰 캐시 (재시작 시 재발급)
_access_token: str | None = None


def get_kis_credentials() -> tuple[str, str, str, str, str]:
    """KIS 환경변수를 읽어 반환한다. 누락 시 ConfigError(503).

    Returns:
        (app_key, app_secret, acnt_no, acnt_prdt_cd_stk, acnt_prdt_cd_fno)
        acnt_prdt_cd_fno는 선택 — 미설정 시 빈 문자열.
    """
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


def get_access_token() -> str:
    """OAuth2 토큰을 발급/캐싱하여 반환한다."""
    global _access_token
    if _access_token:
        return _access_token

    if not KIS_APP_KEY or not KIS_APP_SECRET:
        raise ConfigError("KIS API 키가 설정되지 않았습니다. .env에 KIS_APP_KEY, KIS_APP_SECRET를 설정해주세요.")

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": KIS_APP_KEY,
        "appsecret": KIS_APP_SECRET,
    }
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body), timeout=10)
    except requests.RequestException as e:
        raise ExternalAPIError(f"KIS 토큰 발급 요청 실패: {e}")

    if res.status_code != 200:
        raise ExternalAPIError(f"KIS 토큰 발급 실패: {res.text}")

    _access_token = res.json()["access_token"]
    return _access_token


def clear_token_cache():
    """토큰 캐시 초기화 (만료 시)."""
    global _access_token
    _access_token = None


def issue_hashkey(data: dict) -> str:
    """POST 요청 데이터에 대한 hashkey를 발급한다."""
    url = f"{BASE_URL}/uapi/hashkey"
    headers = {
        "content-type": "application/json",
        "appKey": KIS_APP_KEY,
        "appSecret": KIS_APP_SECRET,
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

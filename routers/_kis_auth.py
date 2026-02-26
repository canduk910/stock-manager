"""KIS API 인증 공통 모듈.

토큰 발급/캐싱, hashkey 발급, 계좌 정보 헬퍼.
balance.py, order.py 등에서 공용으로 사용한다.
"""

import json
import os

import requests
from fastapi import HTTPException

BASE_URL = os.getenv("KIS_BASE_URL") or "https://openapi.koreainvestment.com:9443"

# 인메모리 토큰 캐시 (재시작 시 재발급)
_access_token: str | None = None


def get_kis_credentials() -> tuple[str, str, str, str]:
    """KIS 환경변수를 읽어 반환한다. 누락 시 HTTPException(503)."""
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    acnt_no = os.getenv("KIS_ACNT_NO")
    acnt_prdt_cd = os.getenv("KIS_ACNT_PRDT_CD")

    if not all([app_key, app_secret, acnt_no, acnt_prdt_cd]):
        missing = [
            name for name, val in [
                ("KIS_APP_KEY", app_key),
                ("KIS_APP_SECRET", app_secret),
                ("KIS_ACNT_NO", acnt_no),
                ("KIS_ACNT_PRDT_CD", acnt_prdt_cd),
            ] if not val
        ]
        raise HTTPException(
            status_code=503,
            detail=f"KIS API 키가 설정되지 않았습니다. 누락된 환경변수: {', '.join(missing)}",
        )

    return app_key, app_secret, acnt_no, acnt_prdt_cd


def get_access_token() -> str:
    """OAuth2 토큰을 발급/캐싱하여 반환한다."""
    global _access_token
    if _access_token:
        return _access_token

    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    if not app_key or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="KIS API 키가 설정되지 않았습니다. .env에 KIS_APP_KEY, KIS_APP_SECRET를 설정해주세요.",
        )

    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    try:
        res = requests.post(url, headers={"content-type": "application/json"}, data=json.dumps(body), timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 요청 실패: {e}")

    if res.status_code != 200:
        raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 실패: {res.text}")

    _access_token = res.json()["access_token"]
    return _access_token


def clear_token_cache():
    """토큰 캐시 초기화 (만료 시)."""
    global _access_token
    _access_token = None


def issue_hashkey(data: dict) -> str:
    """POST 요청 데이터에 대한 hashkey를 발급한다."""
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    url = f"{BASE_URL}/uapi/hashkey"
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

"""KIS API 자격증명 검증 모듈.

KIS의 /oauth2/tokenP 엔드포인트로 토큰 발급을 시도해 자격증명이 유효한지 확인.
성공: True. 실패: ExternalAPIError(502) raise.
"""

from __future__ import annotations

import json

import requests

from services.exceptions import ExternalAPIError


_DEFAULT_BASE_URL = "https://openapi.koreainvestment.com:9443"


def validate_kis(app_key: str, app_secret: str, base_url: str | None = None) -> bool:
    """KIS 자격증명 즉시 검증 — 토큰 발급만 시도.

    Args:
        app_key: KIS 앱 키
        app_secret: KIS 앱 시크릿
        base_url: KIS API base URL (실전/모의 구분). None이면 실전.

    Returns:
        True (검증 성공)

    Raises:
        ExternalAPIError: 키 무효, 네트워크 오류, KIS 서버 오류 시.
    """
    url = f"{(base_url or _DEFAULT_BASE_URL).rstrip('/')}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    try:
        res = requests.post(
            url,
            headers={"content-type": "application/json"},
            data=json.dumps(body),
            timeout=10,
        )
    except requests.RequestException as e:
        raise ExternalAPIError(f"KIS 검증 네트워크 오류: {e}")

    if res.status_code != 200:
        # KIS 응답 본문에 상세 에러 메시지 포함
        try:
            err = res.json()
            msg = err.get("error_description") or err.get("msg1") or res.text
        except Exception:
            msg = res.text
        raise ExternalAPIError(f"KIS 인증 실패 (HTTP {res.status_code}): {msg}")

    data = res.json()
    if not data.get("access_token"):
        raise ExternalAPIError("KIS 응답에 access_token 누락")
    return True

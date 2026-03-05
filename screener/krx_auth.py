"""KRX data.krx.co.kr 로그인 세션 관리.

2026-02-27부터 KRX가 데이터 서비스를 로그인 필수로 전환함에 따라,
pykrx 내부 HTTP 세션을 인증된 세션으로 교체하는 우회 방법을 제공한다.

사용법:
    환경변수 KRX_ID, KRX_PASSWORD 설정 후 ensure_krx_session() 호출.
    인증 성공 시 pykrx 전 함수가 정상 동작한다.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── KRX 로그인 엔드포인트 ─────────────────────────────────────────────────────
_LOGIN_PAGE = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001.cmd"
_LOGIN_JSP  = "https://data.krx.co.kr/contents/MDC/COMS/client/view/login.jsp?site=mdc"
_LOGIN_URL  = "https://data.krx.co.kr/contents/MDC/COMS/client/MDCCOMS001D1.cmd"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── 세션 상태 ─────────────────────────────────────────────────────────────────
_shared_session: Optional[requests.Session] = None
_session_ok: bool = False           # 로그인 성공 여부
_last_login_at: float = 0.0         # 마지막 로그인 시각 (epoch)
_SESSION_TTL: float = 60 * 60 * 6  # 세션 유효기간: 6시간


def _inject_session(session: requests.Session) -> None:
    """pykrx 내부 webio 모듈의 HTTP 요청을 인증 세션으로 교체."""
    from pykrx.website.comm import webio

    def _post_read(self, **params):
        return session.post(self.url, headers=self.headers, data=params)

    def _get_read(self, **params):
        return session.get(self.url, headers=self.headers, params=params)

    webio.Post.read = _post_read
    webio.Get.read  = _get_read


def _do_login(login_id: str, login_pw: str) -> tuple[bool, str]:
    """KRX 로그인 수행. (성공 여부, 오류메시지) 반환."""
    session = requests.Session()
    headers_base = {"User-Agent": _UA}

    try:
        session.get(_LOGIN_PAGE, headers=headers_base, timeout=15)
        session.get(_LOGIN_JSP, headers={**headers_base, "Referer": _LOGIN_PAGE}, timeout=15)
    except Exception as e:
        return False, f"KRX 서버 연결 실패: {e}"

    payload = {
        "mbrNm": "", "telNo": "", "di": "", "certType": "",
        "mbrId": login_id,
        "pw": login_pw,
    }
    login_headers = {**headers_base, "Referer": _LOGIN_PAGE}

    try:
        resp = session.post(_LOGIN_URL, data=payload, headers=login_headers, timeout=15)
        data = resp.json()
    except Exception as e:
        return False, f"로그인 응답 파싱 실패: {e}"

    error_code = data.get("_error_code", "")
    error_msg  = data.get("_error_message", "")

    if error_code == "CD011":
        # 중복 로그인 → skipDup=Y 재시도
        payload["skipDup"] = "Y"
        try:
            resp = session.post(_LOGIN_URL, data=payload, headers=login_headers, timeout=15)
            data = resp.json()
            error_code = data.get("_error_code", "")
            error_msg  = data.get("_error_message", "")
        except Exception as e:
            return False, f"중복 로그인 처리 실패: {e}"

    if error_code == "CD001":
        _inject_session(session)
        return True, ""

    return False, f"KRX 로그인 실패 [{error_code}]: {error_msg}"


def ensure_krx_session() -> bool:
    """KRX 인증 세션이 유효한지 확인하고, 필요 시 재로그인.

    KRX_ID / KRX_PASSWORD 환경변수 미설정 시 False 반환 (오류 아님).
    로그인 성공 시 True, 실패 시 False.
    """
    global _session_ok, _last_login_at

    login_id = os.getenv("KRX_ID")
    login_pw = os.getenv("KRX_PASSWORD")

    if not login_id or not login_pw:
        return False  # 환경변수 미설정 → 비인증 상태 (정상적인 미설정)

    now = time.time()
    if _session_ok and (now - _last_login_at) < _SESSION_TTL:
        return True   # 세션 유효

    ok, msg = _do_login(login_id, login_pw)
    if ok:
        _session_ok = True
        _last_login_at = now
        logger.info("KRX 로그인 성공")
    else:
        _session_ok = False
        logger.warning("KRX 로그인 실패: %s", msg)

    return _session_ok


def is_krx_configured() -> bool:
    """KRX 환경변수가 설정되어 있는지 여부."""
    return bool(os.getenv("KRX_ID") and os.getenv("KRX_PASSWORD"))

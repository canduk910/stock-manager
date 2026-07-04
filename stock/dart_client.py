"""OpenDART HTTP 공용 클라이언트 (2026-07-04 refactor F-5).

전송 레이어만 공용화 — Connection: close 헤더 + ConnectionError 재시도.
screener/dart.py의 `_dart_get`(2026 RemoteDisconnected 대응)을 표준으로 승격했다.
파라미터 구성/응답 파싱/status 해석은 각 호출 모듈이 유지한다
(공시 분류·사업보고서 추출·HBM 수주 스캔은 도메인별 규칙이 다름).
"""

from __future__ import annotations

import time

import requests

# keep-alive 재사용 방지 → DART 서버 RemoteDisconnected 방지
DART_HEADERS = {"Connection": "close"}


def dart_get(url: str, params: dict, timeout: int = 30, retries: int = 3) -> requests.Response:
    """DART API GET 요청.

    ConnectionError 발생 시 최대 retries회 재시도 (1s / 2s ... 지수 간격).
    HTTP status 검사는 하지 않는다 — 호출자가 상태코드/DART status 필드를 해석.
    """
    last_exc: Exception = RuntimeError("no attempt")
    for attempt in range(retries):
        try:
            return requests.get(url, params=params, timeout=timeout, headers=DART_HEADERS)
        except requests.exceptions.ConnectionError as e:
            last_exc = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise last_exc

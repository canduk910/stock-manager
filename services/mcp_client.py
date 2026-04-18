"""MCP HTTP 클라이언트 — KIS AI Extensions 서버 통신.

KIS AI Extensions MCP 서버와 JSON-RPC 2.0 프로토콜로 통신한다.
백테스트 도구(list_presets_tool, run_preset_backtest_tool, validate_yaml_tool 등)를
HTTP POST로 호출하여 결과를 반환한다.

의존 관계:
- config.py → KIS_MCP_ENABLED (기본 false), KIS_MCP_URL
- services/exceptions.py → ConfigError, ExternalAPIError

사용처:
- backtest_service.py → call_tool()로 프리셋/커스텀 백테스트 실행
- advisory_service.py → 전략 신호 수집 시 간접 호출

KIS_MCP_ENABLED=false(기본)이면 모든 도구 호출에서 ConfigError를 raise하며,
health_check()만 예외로 False를 반환한다 (graceful degrade 지원).
"""

import logging

import httpx

from config import KIS_MCP_ENABLED, KIS_MCP_URL
from services.exceptions import ConfigError, ExternalAPIError

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Streamable HTTP 클라이언트.

    MCP 2025-03-26 프로토콜 — 세션 기반 Streamable HTTP:
    1. POST /mcp + initialize → 세션 ID 획득 (응답 헤더 mcp-session-id)
    2. POST /mcp + tools/call (헤더에 Mcp-Session-Id) → SSE 응답에서 result 추출
    """

    def __init__(self):
        mcp_url = KIS_MCP_URL.rstrip("/")
        if mcp_url.endswith("/mcp"):
            self._base_url = mcp_url[:-4]
            self._mcp_path = "/mcp"
        else:
            self._base_url = mcp_url
            self._mcp_path = ""
        # MCP 서버가 Host 헤더를 검증하므로, 127.0.0.1로 고정
        # (Docker 내부에서 host.docker.internal로 접근 시 Host 불일치 방지)
        from urllib.parse import urlparse
        parsed = urlparse(mcp_url)
        self._host_header = f"127.0.0.1:{parsed.port or 3846}"
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(connect=5.0, read=300.0, write=10.0, pool=10.0),
        )
        self._req_id = 0
        self._session_id: str | None = None

    def _check_enabled(self):
        if not KIS_MCP_ENABLED:
            raise ConfigError("KIS MCP 서버가 비활성화되어 있습니다. KIS_MCP_ENABLED=true로 설정하세요.")

    def _ensure_session(self):
        """MCP 세션 초기화. 세션 ID가 없거나 만료 시 재초기화."""
        if self._session_id:
            return
        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "stock-manager", "version": "1.0"},
            },
        }
        try:
            resp = self._http.post(
                self._mcp_path,
                json=payload,
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                    "Host": self._host_header,
                },
            )
            resp.raise_for_status()
            self._session_id = resp.headers.get("mcp-session-id", "")
            logger.info("MCP 세션 초기화 완료: %s", self._session_id[:8] if self._session_id else "N/A")
        except Exception as e:
            logger.warning("MCP 세션 초기화 실패: %s", e)
            self._session_id = None

    def _parse_sse_result(self, text: str) -> dict:
        """SSE 텍스트에서 JSON-RPC result 추출."""
        import json as _json
        for line in text.split("\n"):
            if line.startswith("data: "):
                try:
                    body = _json.loads(line[6:])
                    if "error" in body:
                        raise ExternalAPIError(f"MCP 도구 호출 실패: {body['error']}")
                    return body.get("result", {})
                except _json.JSONDecodeError:
                    continue
        # SSE가 아닌 일반 JSON 응답일 수도 있음
        try:
            body = _json.loads(text)
            if "error" in body:
                raise ExternalAPIError(f"MCP 도구 호출 실패: {body['error']}")
            return body.get("result", {})
        except _json.JSONDecodeError:
            raise ExternalAPIError(f"MCP 응답 파싱 실패: {text[:200]}")

    def call_tool(self, tool_name: str, params: dict) -> dict:
        """MCP tools/call 호출 (Streamable HTTP 세션 프로토콜)."""
        self._check_enabled()
        self._ensure_session()
        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": params},
        }
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Host": self._host_header,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        try:
            resp = self._http.post(self._mcp_path, json=payload, headers=headers)
            # 421 = 세션 만료 → 재초기화 후 재시도
            if resp.status_code == 421:
                self._session_id = None
                self._ensure_session()
                if self._session_id:
                    headers["Mcp-Session-Id"] = self._session_id
                resp = self._http.post(self._mcp_path, json=payload, headers=headers)
            resp.raise_for_status()
            return self._parse_sse_result(resp.text)
        except httpx.ConnectError:
            raise ExternalAPIError("KIS MCP 서버에 연결할 수 없습니다")
        except httpx.TimeoutException:
            raise ExternalAPIError("MCP 서버 응답 시간 초과")
        except httpx.HTTPStatusError as e:
            raise ExternalAPIError(f"MCP 서버 HTTP 오류: {e.response.status_code}")

    def health_check(self) -> bool:
        """MCP 서버 상태 확인."""
        if not KIS_MCP_ENABLED:
            return False
        try:
            resp = self._http.get("/health", timeout=3.0)
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False


# ── 싱글턴 ──────────────────────────────────────────────────────────────────
# 모듈 레벨 전역 변수로 MCPClient 인스턴스를 1개만 유지한다.
# httpx.Client 내부 커넥션 풀을 재사용하여 연결 오버헤드를 줄인다.

_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """MCPClient 싱글턴. 최초 호출 시 인스턴스를 생성하고 이후 재사용한다."""
    global _client
    if _client is None:
        _client = MCPClient()
    return _client

"""MCP HTTP 클라이언트 — KIS AI Extensions 서버 통신.

MCP JSON-RPC 프로토콜로 백테스트 도구 호출.
KIS_MCP_ENABLED=false(기본)이면 ConfigError raise.
"""

import logging

import httpx

from config import KIS_MCP_ENABLED, KIS_MCP_URL
from services.exceptions import ConfigError, ExternalAPIError

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 서버 동기 HTTP 클라이언트."""

    def __init__(self):
        self._http = httpx.Client(
            base_url=KIS_MCP_URL,
            timeout=httpx.Timeout(connect=5.0, read=300.0, write=10.0, pool=10.0),
        )
        self._req_id = 0

    def _check_enabled(self):
        """MCP 비활성화 시 ConfigError raise."""
        if not KIS_MCP_ENABLED:
            raise ConfigError("KIS MCP 서버가 비활성화되어 있습니다. KIS_MCP_ENABLED=true로 설정하세요.")

    def call_tool(self, tool_name: str, params: dict) -> dict:
        """MCP JSON-RPC tools/call 호출."""
        self._check_enabled()
        self._req_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": params},
        }
        try:
            resp = self._http.post("", json=payload)
            resp.raise_for_status()
            body = resp.json()
            if "error" in body:
                raise ExternalAPIError(f"MCP 도구 호출 실패: {body['error']}")
            return body.get("result", {})
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


_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    """MCPClient 싱글턴."""
    global _client
    if _client is None:
        _client = MCPClient()
    return _client

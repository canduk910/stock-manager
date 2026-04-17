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
    """MCP 서버 동기 HTTP 클라이언트.

    httpx.Client 기반이며, JSON-RPC 2.0 페이로드를 구성하여 MCP 서버에 전송한다.
    """

    def __init__(self):
        # connect=5s: 로컬/사내 서버 연결이므로 5초면 충분
        # read=300s: 백테스트 실행이 최대 5분까지 소요될 수 있음
        # write=10s, pool=10s: 일반적인 HTTP 클라이언트 기본값
        self._http = httpx.Client(
            base_url=KIS_MCP_URL,
            timeout=httpx.Timeout(connect=5.0, read=300.0, write=10.0, pool=10.0),
        )
        # JSON-RPC 요청 ID — 호출마다 1씩 증가하여 요청/응답 매칭에 사용
        self._req_id = 0

    def _check_enabled(self):
        """MCP 비활성화 시 ConfigError raise."""
        if not KIS_MCP_ENABLED:
            raise ConfigError("KIS MCP 서버가 비활성화되어 있습니다. KIS_MCP_ENABLED=true로 설정하세요.")

    def call_tool(self, tool_name: str, params: dict) -> dict:
        """MCP JSON-RPC tools/call 호출.

        JSON-RPC 2.0 페이로드 구조:
        {
            "jsonrpc": "2.0",
            "id": <순차 증가 정수>,
            "method": "tools/call",
            "params": {"name": <도구명>, "arguments": <파라미터 dict>}
        }

        에러 변환 규칙:
        - httpx.ConnectError → ExternalAPIError("연결 불가")
        - httpx.TimeoutException → ExternalAPIError("응답 시간 초과")
        - httpx.HTTPStatusError → ExternalAPIError("HTTP 오류: {status_code}")
        - body에 "error" 키 존재 → ExternalAPIError("도구 호출 실패")
        """
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
        """MCP 서버 상태 확인.

        MCP 비활성화 시에도 에러를 raise하지 않고 False를 반환한다 (graceful degrade).
        이를 통해 호출자가 MCP 사용 가능 여부를 안전하게 판별할 수 있다.
        """
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

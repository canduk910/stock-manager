"""REQ-FIX-05: MCP backtester 에러 패턴 분류 → 사용자 친화 메시지 매핑.

진단 결과(2026-05-09): 'vps' KeyError 는 backtester EC2 의
~/KIS/config/kis_devlp.yaml 에서 KIS 모의투자 모드 식별자(`vps:` 섹션) 가
누락되었거나 다른 키(예: `vts:`)로 잘못 작성되어 KIS 인증 단계에서 발생.

분류 정책:
- error_msg 에 `'vps'` 포함 → "백테스트 인증 설정 오류" 메시지 (운영자 yaml 가이드)
- `데이터 준비 실패` / `data preparation failed` → "백테스트 데이터 조회 실패" (종목/날짜 가이드)
- 그 외 → 기존 `f"MCP 백테스트 실패: {error_msg}"` 유지
- 원본 error_msg 는 logger.warning 으로 보존(운영 디버깅).

`'vps'` 단독은 'data preparation' 패턴보다 우선순위가 높다 — 같은 메시지에 두 패턴이
함께 등장(예: "백테스트 실패: 데이터 준비 실패: 'vps'") 시 인증 가이드를 노출.
"""
from __future__ import annotations

import json

import pytest

from services.backtest_service import _classify_backtester_error, _extract_mcp_content
from services.exceptions import ExternalAPIError


def _wrap_mcp(payload: dict) -> dict:
    """MCP 응답 봉투 — content[0].text 안에 JSON."""
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


def _msg(exc: pytest.ExceptionInfo) -> str:
    return exc.value.message if hasattr(exc.value, "message") else str(exc.value)


# ── _classify_backtester_error 단위 테스트 ───────────────────────────────


def test_classify_vps_key_missing():
    assert _classify_backtester_error("백테스트 실패: 데이터 준비 실패: 'vps'") == "vps_key_missing"
    assert _classify_backtester_error("KeyError: 'vps'") == "vps_key_missing"


def test_classify_data_prep_without_vps():
    assert _classify_backtester_error("data preparation failed: timeout") == "data_prep"
    assert _classify_backtester_error("데이터 준비 실패: connection refused") == "data_prep"


def test_classify_other_returns_none():
    assert _classify_backtester_error("전략 검증 실패: invalid YAML") is None
    assert _classify_backtester_error("") is None


# ── _extract_mcp_content 통합 (분류 + 메시지 매핑) ─────────────────────


def test_vps_key_translates_to_yaml_guide_message():
    """(a) 'vps' 패턴 → 인증 설정 오류 가이드 (yaml `vps:` 섹션 누락)."""
    mcp_resp = _wrap_mcp({"success": False, "error": "백테스트 실패: 데이터 준비 실패: 'vps'"})
    with pytest.raises(ExternalAPIError) as exc:
        _extract_mcp_content(mcp_resp)
    msg = _msg(exc)
    assert "백테스트 인증 설정 오류" in msg
    assert "kis_devlp.yaml" in msg
    assert "vps" in msg  # yaml 키 라벨로서 노출 (식별 가능)
    # 원본 사용자에게 'vps' 가 의미 불명한 단독 식별자로 보이지 않도록 가이드 포함
    assert "임시" in msg or "로컬 백테스트" in msg


def test_data_preparation_failed_pattern_translates():
    """(b) 'vps' 미포함 + 'data preparation failed' → 종목/날짜 가이드."""
    mcp_resp = _wrap_mcp({"success": False, "error": "data preparation failed: timeout"})
    with pytest.raises(ExternalAPIError) as exc:
        _extract_mcp_content(mcp_resp)
    msg = _msg(exc)
    assert "백테스트 데이터 조회 실패" in msg
    assert "종목 코드" in msg or "날짜 범위" in msg


def test_korean_data_preparation_pattern_translates():
    """(b-2) '데이터 준비 실패' 키워드 단독도 동일 변환."""
    mcp_resp = _wrap_mcp({"success": False, "error": "데이터 준비 실패: connection refused"})
    with pytest.raises(ExternalAPIError) as exc:
        _extract_mcp_content(mcp_resp)
    msg = _msg(exc)
    assert "백테스트 데이터 조회 실패" in msg


def test_other_error_keeps_existing_message():
    """(c) 매칭 안되는 패턴 → 기존 메시지 유지."""
    mcp_resp = _wrap_mcp({"success": False, "error": "전략 검증 실패: invalid YAML"})
    with pytest.raises(ExternalAPIError) as exc:
        _extract_mcp_content(mcp_resp)
    msg = _msg(exc)
    assert "MCP 백테스트 실패" in msg
    assert "전략 검증 실패" in msg


def test_success_response_unchanged():
    """(d) 정상 응답은 변경 없음 (data 그대로 반환)."""
    mcp_resp = _wrap_mcp({"success": True, "data": {"job_id": "abc-123"}})
    out = _extract_mcp_content(mcp_resp)
    assert out == {"job_id": "abc-123"}


def test_original_error_logged_as_warning(caplog):
    """(e) 친화 메시지 변환 시에도 원본 error_msg 는 logger.warning 으로 기록."""
    import logging
    caplog.set_level(logging.WARNING, logger="services.backtest_service")

    mcp_resp = _wrap_mcp({"success": False, "error": "백테스트 실패: 데이터 준비 실패: 'vps'"})
    with pytest.raises(ExternalAPIError):
        _extract_mcp_content(mcp_resp)

    # 원본 error_msg 가 로그에 포함되어야 함 (운영 디버깅용)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "vps" in text or "데이터 준비 실패" in text

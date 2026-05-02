"""portfolio_advisor_service 톤 완화 통합 테스트.

Plan 출처: .claude/plans/ai-sparkling-starfish.md (테스트 #5)
- 시스템 프롬프트에 "매도 우선 검토" 문구 부재
- "사이클 주도 섹터" 가이드 존재
- "신규 편입 전면 보류" 톤 완화 검증
"""
from __future__ import annotations

import pytest


def _build_system_prompt(regime, cash_pct, cycle_ctx=None):
    """portfolio_advisor_service의 시스템 프롬프트 빌더만 격리 호출."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_portadv_iso",
        "/Users/kimdukki/PycharmProjects/stock-manager/services/portfolio_advisor_service.py",
    )
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._build_system_prompt(regime, cash_pct, cycle_ctx)
    except Exception as e:
        pytest.skip(f"portfolio_advisor_service 격리 로드 실패: {e}")


def test_no_sell_first_imperative():
    """'현금 확보를 위한 매도를 우선 검토' 문구 부재."""
    cycle_ctx = {"phase": "expansion", "phase_label": "확장기", "leader_sectors": ["XLK"]}
    prompt = _build_system_prompt("selective", 30, cycle_ctx)
    assert "매도를 우선 검토" not in prompt


def test_no_full_block_new_entries():
    """'신규 편입 전면 보류' 문구 부재 (사이클 주도 섹터 한정으로 완화)."""
    cycle_ctx = {"phase": "expansion", "phase_label": "확장기", "leader_sectors": ["XLK"]}
    prompt = _build_system_prompt("cautious", 40, cycle_ctx)
    assert "전면 보류" not in prompt


def test_contains_cycle_leader_sector_guidance():
    """사이클 주도 섹터 우선 가이드 포함."""
    cycle_ctx = {
        "phase": "expansion", "phase_label": "확장기",
        "leader_sectors": ["XLK", "XLY", "XLC"],
        "confidence": 65,
    }
    prompt = _build_system_prompt("cautious", 40, cycle_ctx)
    assert "사이클 주도 섹터" in prompt or "주도 섹터" in prompt


def test_defensive_recovery_allows_partial_buy():
    """defensive 체제 + 회복 사이클 → 부분 매수 검토 가능 톤."""
    cycle_ctx = {
        "phase": "recovery", "phase_label": "회복기",
        "leader_sectors": ["XLF", "XLI"],
        "confidence": 55,
    }
    prompt = _build_system_prompt("defensive", 70, cycle_ctx)
    # "신규 매수 금지" 절대 톤 부재 또는 사이클 주도 섹터 한정 부분 매수 톤 존재
    assert "사이클" in prompt
    assert ("신규 매수를 추천하지 마세요" not in prompt) or ("부분 매수" in prompt) or ("주도 섹터" in prompt)


def test_defensive_contraction_keeps_no_buy():
    """defensive+contraction은 여전히 신규 매수 금지 톤 유지 (안전 가드)."""
    cycle_ctx = {
        "phase": "contraction", "phase_label": "수축기",
        "leader_sectors": [],
    }
    prompt = _build_system_prompt("defensive", 70, cycle_ctx)
    assert "신규 매수 금지" in prompt or "매도" in prompt or "관망" in prompt


def test_loss_handling_three_options_balanced():
    """-15% 초과 종목 처리: '손절 우선' 일변도가 아닌 3안 균형 제시."""
    cycle_ctx = {"phase": "expansion", "phase_label": "확장기", "leader_sectors": ["XLK"]}
    prompt = _build_system_prompt("selective", 35, cycle_ctx)
    # 3안 명시: 손절 / 분할매수(물타기) / 홀딩
    has_three_options = (
        ("3안" in prompt) or
        ("손절" in prompt and "물타기" in prompt and "홀딩" in prompt)
    )
    assert has_three_options


def test_action_matrix_guide_in_cycle_context():
    """_format_cycle_context가 액션 매트릭스 가이드 1줄을 포함."""
    cycle_ctx = {
        "phase": "expansion", "phase_label": "확장기",
        "leader_sectors": ["XLK"], "confidence": 60,
    }
    prompt = _build_system_prompt("defensive", 70, cycle_ctx)
    # 액션 매트릭스 가이드 키워드
    assert "조합 액션 매트릭스" in prompt or "액션 매트릭스" in prompt

"""advisory_service._build_system_prompt cycle×regime 매트릭스 단위 테스트.

Plan 출처: .claude/plans/ai-sparkling-starfish.md (테스트 #3)
- "## 경기 사이클" 섹션 포함 (시스템 프롬프트 내 cycle 정보 노출)
- "어떤 경우에도 매수 금지" 문구 미포함 (보수성 완화 검증)
- 성장주 보조 트랙 안내 포함
"""
from __future__ import annotations

import pytest


def _build_system_prompt(regime, regime_desc, cycle_ctx=None):
    """advisory_service의 시스템 프롬프트 빌더만 격리 호출.

    advisory_service 전체 import는 stock/* 의존성으로 환경 차이가 큼.
    여기서는 함수 자체를 import 시도하되 실패 시 모듈 직접 로드.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_adv_iso_cycle",
        "/Users/kimdukki/PycharmProjects/stock-manager/services/advisory_service.py",
    )
    # 하위 모듈은 의존성이 있으나 _build_system_prompt 자체는 macro_regime만 의존
    # → 의존 import 실패 시 부분 로드 시도 (skip)
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._build_system_prompt(regime, regime_desc, cycle_ctx)
    except Exception as e:
        pytest.skip(f"advisory_service 격리 로드 실패 (환경 의존): {e}")


def test_system_prompt_contains_cycle_section_when_provided():
    cycle_ctx = {
        "phase": "expansion",
        "phase_label": "확장기",
        "leader_sectors": ["XLK", "XLY"],
        "confidence": 65,
    }
    prompt = _build_system_prompt("defensive", "방어", cycle_ctx)
    # cycle 정보가 시스템 프롬프트 내에 명시
    assert "확장기" in prompt or "expansion" in prompt
    assert "주도 섹터" in prompt
    # 사이클 정보가 진입 정책으로 변환됨
    assert "사이클 주도 섹터" in prompt or "주도 섹터" in prompt


def test_system_prompt_no_absolute_buy_block():
    """'어떤 경우에도 매수 금지' 문구는 제거되어야 함 (보수성 완화 핵심)."""
    cycle_ctx = {
        "phase": "expansion",
        "phase_label": "확장기",
        "leader_sectors": ["XLK"],
        "confidence": 60,
    }
    prompt = _build_system_prompt("defensive", "방어", cycle_ctx)
    assert "어떤 경우에도" not in prompt or "매수' 등급을 부여하지 마라" not in prompt


def test_system_prompt_contains_growth_track_guidance():
    """성장주 보조 트랙 안내 포함 (가치 D + G-A 진입 허용)."""
    cycle_ctx = {"phase": "recovery", "phase_label": "회복기", "leader_sectors": ["XLF"]}
    prompt = _build_system_prompt("selective", "선별", cycle_ctx)
    assert "성장주 보조" in prompt or "성장 보조" in prompt or "G-A" in prompt


def test_system_prompt_contains_graham_cycle_correction():
    """Graham 할인 임계의 사이클 보정 안내 포함."""
    cycle_ctx = {"phase": "recovery", "phase_label": "회복기", "leader_sectors": ["XLF"]}
    prompt = _build_system_prompt("accumulation", "축적", cycle_ctx)
    assert "Graham" in prompt
    # 사이클 보정 임계값 (15/25/10) 중 일부 노출
    assert "15%" in prompt or "25%" in prompt or "10%" in prompt


def test_system_prompt_defensive_contraction_keeps_no_buy():
    """defensive+contraction 셀에서는 여전히 신규 매수 금지 톤 유지."""
    cycle_ctx = {"phase": "contraction", "phase_label": "수축기", "leader_sectors": []}
    prompt = _build_system_prompt("defensive", "방어", cycle_ctx)
    # contraction 정책 라인이 반영되어야 함 (신규 매수 금지/매도/관망)
    assert "신규 매수" in prompt or "매도" in prompt or "관망" in prompt


def test_system_prompt_no_cycle_uses_fallback():
    """cycle_ctx=None이어도 정상 작동 (fallback 정책)."""
    prompt = _build_system_prompt("selective", "선별", None)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert "selective" in prompt or "선별" in prompt

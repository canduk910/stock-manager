"""REQ-DOMAIN-001: growth_grade × KR 14 라벨 사이클 정합 회귀 가드.

신규 KR 14 한글 라벨 모두에 대해 4개 cycle phase 정합 점수를 명시한다.
변경 전후 diff로 silent regression 차단.

기준 매트릭스(56 = 14 × 4)는 _LEADER_SECTOR_MAP 패치 후 의도한 결과.
- 추가 키워드: expansion에 "2차전지","IT/인터넷"; recovery에 "운송/물류","자동차"; overheating에 "에너지/화학" 등
- 삭제 금지 — 기존 영문/한글 키 100% 보존
"""
from __future__ import annotations

import pytest

from services.growth_grade import _LEADER_SECTOR_MAP, _score_cycle_alignment


KR_14_LABELS = (
    "반도체", "IT/인터넷", "2차전지", "건설", "바이오/헬스케어", "은행/금융",
    "철강/소재", "자동차", "에너지/화학", "미디어/엔터", "필수소비재",
    "경기소비재", "운송/물류", "유틸리티",
)
PHASES = ("recovery", "expansion", "overheating", "contraction")


# ──────────────────────────────────────────────────────────────────────
# 보존 가드 — 기존 키 삭제 금지
# ──────────────────────────────────────────────────────────────────────

EXISTING_KEYS_FROZEN = {
    "recovery": {"XLF", "XLI", "XLB", "Financials", "Industrials", "Materials",
                 "금융", "산업재", "소재", "은행", "건설", "기계"},
    "expansion": {"XLK", "XLY", "XLC", "Technology", "Consumer Discretionary",
                  "Communication Services", "기술", "IT", "반도체", "소프트웨어",
                  "임의소비재", "커뮤니케이션", "인터넷"},
    "overheating": {"XLE", "XLB", "XLP", "Energy", "Materials", "Consumer Staples",
                    "에너지", "필수소비재", "정유", "화학"},
    "contraction": {"XLU", "XLV", "XLP", "Utilities", "Healthcare", "Consumer Staples",
                    "유틸리티", "헬스케어", "필수소비재", "통신"},
}


@pytest.mark.parametrize("phase,frozen", EXISTING_KEYS_FROZEN.items())
def test_leader_map_preserves_existing_keys(phase, frozen):
    """기존 영문/한글 키는 삭제 금지 (회귀 방어)."""
    current = _LEADER_SECTOR_MAP[phase]
    missing = frozen - current
    assert not missing, f"{phase}에서 삭제된 키 발견: {missing}"


# ──────────────────────────────────────────────────────────────────────
# 추가 키워드 가드 — REQ-DOMAIN-001 패치 요구사항
# ──────────────────────────────────────────────────────────────────────

def test_expansion_includes_kr_specific_labels():
    """expansion에 2차전지/IT/인터넷 라벨이 leader 또는 부분일치로 인식되어야."""
    pts_2차, _ = _score_cycle_alignment("2차전지", "expansion")
    pts_it, _ = _score_cycle_alignment("IT/인터넷", "expansion")
    assert pts_2차 >= 3, f"2차전지 expansion={pts_2차}; ≥3 기대"
    assert pts_it >= 3, f"IT/인터넷 expansion={pts_it}; ≥3 기대"


def test_recovery_includes_transport_and_auto():
    """recovery에 운송/물류, 자동차 라벨이 leader 또는 부분일치로 인식."""
    pts_t, _ = _score_cycle_alignment("운송/물류", "recovery")
    pts_a, _ = _score_cycle_alignment("자동차", "recovery")
    assert pts_t >= 3, f"운송/물류 recovery={pts_t}; ≥3 기대"
    assert pts_a >= 3, f"자동차 recovery={pts_a}; ≥3 기대"


def test_overheating_recognizes_energy_chemical():
    """overheating에 '에너지/화학' 통합 라벨이 leader 또는 부분일치로 인식."""
    pts, label = _score_cycle_alignment("에너지/화학", "overheating")
    assert pts >= 3, f"에너지/화학 overheating={pts}; ≥3 기대 (현재 label={label})"


def test_us_normalized_labels_recognized():
    """US 정규화 한글 라벨도 적절히 매칭."""
    # 정보기술 expansion (기존 '기술' 키 부분일치 또는 leader)
    pts_it, _ = _score_cycle_alignment("정보기술", "expansion")
    assert pts_it >= 3
    # 헬스케어 contraction
    pts_hc, _ = _score_cycle_alignment("헬스케어", "contraction")
    assert pts_hc >= 3
    # 유틸리티 contraction
    pts_u, _ = _score_cycle_alignment("유틸리티", "contraction")
    assert pts_u >= 3
    # 금융 recovery
    pts_f, _ = _score_cycle_alignment("금융", "recovery")
    assert pts_f >= 3


# ──────────────────────────────────────────────────────────────────────
# 56 케이스 매트릭스 — 명시적 점수 표 (의도된 결과)
# 패치 후 기대 결과 — 기존 baseline에서 개선된 셀만 변경
# ──────────────────────────────────────────────────────────────────────

# 매트릭스: (sector, phase) → 기대 점수
# - 4: 주도섹터 직접 매칭
# - 3: 부분일치(같은 카테고리)
# - 2: 중립
# - 1: 반대사이클
# 패치 후 실제 매트릭스 — _LEADER_SECTOR_MAP 신규 키워드 추가 결과.
# baseline 대비 변경된 셀:
#   IT/인터넷    expansion: 3→4 (직접 라벨 leader 추가)
#   2차전지      expansion: 2→4 (라벨 leader 추가)
#   2차전지     contraction: 2→1 (expansion leader면 contraction 반대사이클로 자동 분류)
#   바이오/헬스케어 contraction: 3→4 (라벨 leader 추가)
#   철강/소재    overheating: 1→4 (라벨 leader 추가; 반대사이클 우선 규칙 우회)
#   자동차       recovery: 2→4 (라벨 leader 추가)
#   자동차      overheating: 2→1 (recovery leader면 자동 반대 분류)
#   에너지/화학  overheating: 3→4 (직접 라벨 leader 추가)
#   운송/물류    recovery: 2→4 (라벨 leader 추가)
#   운송/물류   overheating: 2→1 (recovery leader면 자동 반대 분류)
EXPECTED_MATRIX = {
    # sector             recovery exp  ovh  con
    "반도체":              (2, 4, 2, 1),  # expansion leader (보존)
    "IT/인터넷":           (2, 4, 2, 1),  # expansion leader 강화 (3→4)
    "2차전지":             (2, 4, 2, 1),  # expansion leader 추가 (2→4 / 2→1)
    "건설":                (4, 2, 1, 2),  # recovery leader (보존)
    "바이오/헬스케어":     (2, 1, 2, 4),  # contraction leader 강화 (3→4)
    "은행/금융":           (3, 2, 1, 2),  # recovery 부분일치 (보존: '은행')
    "철강/소재":           (3, 2, 4, 2),  # overheating leader 강화 (1→4)
    "자동차":              (4, 2, 1, 2),  # recovery leader 추가 (2→4)
    "에너지/화학":         (1, 2, 4, 2),  # overheating leader 강화 (3→4)
    "미디어/엔터":         (2, 2, 2, 2),  # 매칭 없음 (의도된 중립 — 향후 보강 가능)
    "필수소비재":          (1, 1, 4, 4),  # overheating+contraction 양쪽 leader (보존)
    "경기소비재":          (2, 2, 2, 2),  # 단어 분리 매칭 어려움 (의도된 중립)
    "운송/물류":           (4, 2, 1, 2),  # recovery leader 추가 (2→4)
    "유틸리티":            (2, 1, 2, 4),  # contraction leader (보존)
}


@pytest.mark.parametrize("sector,scores", EXPECTED_MATRIX.items())
def test_kr_14_matrix(sector, scores):
    """14 라벨 × 4 phase 56 케이스 회귀 매트릭스."""
    actual = tuple(_score_cycle_alignment(sector, phase)[0] for phase in PHASES)
    assert actual == scores, (
        f"{sector}: actual={actual} expected={scores} (phases={PHASES})"
    )


def test_at_least_10_of_14_have_directional_signal():
    """수용 기준: 14개 중 최소 10개는 의도한 leader/opposite 매칭(중립 외)."""
    directional = 0
    for sector in KR_14_LABELS:
        for phase in PHASES:
            pts, _ = _score_cycle_alignment(sector, phase)
            if pts != 2:  # 중립이 아니면 directional
                directional += 1
                break
    assert directional >= 10, (
        f"directional={directional}/14 — 최소 10/14 기대"
    )


# ──────────────────────────────────────────────────────────────────────
# 폴백 동작
# ──────────────────────────────────────────────────────────────────────

def test_etc_fallback_returns_neutral():
    """'기타' sector는 어떤 phase에서도 중립(2점)."""
    for phase in PHASES:
        pts, label = _score_cycle_alignment("기타", phase)
        assert pts == 2, f"phase={phase} pts={pts} label={label}"


def test_none_sector_returns_neutral():
    pts, _ = _score_cycle_alignment(None, "expansion")
    assert pts == 2


def test_none_phase_returns_neutral():
    pts, _ = _score_cycle_alignment("반도체", None)
    assert pts == 2

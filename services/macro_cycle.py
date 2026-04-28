"""경기 사이클 국면 판단.

macro_regime.py와 완전 독립. 수익률곡선, 신용스프레드, VIX,
섹터 로테이션, 달러 강도 5개 지표 가중합산으로 4국면 판단.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 4국면 정의 ──────────────────────────────────────────────────────────────

CYCLE_PHASES = {
    "recovery": {
        "label": "회복기",
        "desc": "수익률곡선 정상화, VIX 하락, 신용스프레드 축소",
    },
    "expansion": {
        "label": "확장기",
        "desc": "양의 수익률곡선, 낮은 VIX, 좁은 신용스프레드",
    },
    "overheating": {
        "label": "과열기",
        "desc": "수익률곡선 평탄화, VIX 저점, 방어 전환",
    },
    "contraction": {
        "label": "수축기",
        "desc": "수익률곡선 역전, VIX 급등, 신용스프레드 확대",
    },
}

# ── 국면별 선도 섹터 ────────────────────────────────────────────────────────

LEADER_SECTORS = {
    "recovery": ["XLF", "XLI", "XLB"],
    "expansion": ["XLK", "XLY", "XLC"],
    "overheating": ["XLE", "XLB", "XLP"],
    "contraction": ["XLU", "XLV", "XLP"],
}


# ── 점수 계산 ───────────────────────────────────────────────────────────────

def _score_yield_curve(
    spread: Optional[float],
    direction: str,
) -> dict[str, float]:
    """수익률곡선 30% 가중치 점수."""
    scores = {"recovery": 0, "expansion": 0, "overheating": 0, "contraction": 0}

    if spread is None:
        return scores

    if spread > 1.5:
        scores["recovery"] = 0.7
        scores["expansion"] = 0.3
    elif spread > 0:
        scores["expansion"] = 0.5
        scores["overheating"] = 0.5
    else:  # 역전
        scores["contraction"] = 1.0

    # 방향 보정
    if direction == "steepening":
        scores["recovery"] += 0.3
    elif direction == "flattening":
        scores["overheating"] += 0.3

    return scores


def _score_credit(direction: str) -> dict[str, float]:
    """하이일드 신용스프레드 20% 가중치 점수."""
    scores = {"recovery": 0, "expansion": 0, "overheating": 0, "contraction": 0}

    if direction == "narrowing":
        scores["recovery"] = 0.5
        scores["expansion"] = 0.5
    elif direction == "widening":
        scores["contraction"] = 1.0
    else:
        scores["expansion"] = 0.3
        scores["overheating"] = 0.3

    return scores


def _score_vix(value: Optional[float], level: str) -> dict[str, float]:
    """VIX 20% 가중치 점수."""
    scores = {"recovery": 0, "expansion": 0, "overheating": 0, "contraction": 0}

    if value is None:
        return scores

    if value > 35:
        # 강제 contraction
        scores["contraction"] = 1.0
        return scores

    if value < 15:
        scores["expansion"] = 0.7
        scores["overheating"] = 0.3
    elif value < 25:
        scores["expansion"] = 0.3
        scores["recovery"] = 0.3
        scores["overheating"] = 0.2
    else:  # 25~35
        scores["contraction"] = 0.7
        scores["recovery"] = 0.3

    return scores


def _score_sector(rotation: str) -> dict[str, float]:
    """섹터 로테이션 15% 가중치 점수."""
    scores = {"recovery": 0, "expansion": 0, "overheating": 0, "contraction": 0}

    if rotation == "cyclical":
        scores["expansion"] = 0.7
        scores["recovery"] = 0.3
    elif rotation == "defensive":
        scores["contraction"] = 0.7
        scores["overheating"] = 0.3
    else:
        scores["expansion"] = 0.25
        scores["overheating"] = 0.25

    return scores


def _score_dollar(strength: str) -> dict[str, float]:
    """달러 강도 15% 가중치 점수."""
    scores = {"recovery": 0, "expansion": 0, "overheating": 0, "contraction": 0}

    if strength == "weakening":
        scores["expansion"] = 0.7
        scores["recovery"] = 0.3
    elif strength == "strengthening":
        scores["contraction"] = 0.7
        scores["overheating"] = 0.3
    else:
        scores["expansion"] = 0.25
        scores["overheating"] = 0.25

    return scores


# ── 국면 판단 ───────────────────────────────────────────────────────────────

def determine_cycle_phase(inputs: dict) -> dict:
    """5개 지표로 경기 사이클 국면 판단.

    Args:
        inputs: fetch_cycle_inputs() 반환값
            - yield_spread, yield_direction, credit_direction,
              vix_value, vix_level, sector_rotation, dollar_strength

    Returns:
        {
            "phase": str,          # recovery / expansion / overheating / contraction
            "label": str,          # 한글 레이블
            "description": str,    # 설명
            "confidence": int,     # 0~100
            "scores": dict,        # 국면별 점수
            "leader_sectors": list, # 선도 섹터 ETF 심볼
            "inputs_summary": dict, # 입력 지표 요약
        }
    """
    # 가중치
    weights = {
        "yield": 0.30,
        "credit": 0.20,
        "vix": 0.20,
        "sector": 0.15,
        "dollar": 0.15,
    }

    # 개별 점수 계산
    s_yield = _score_yield_curve(inputs.get("yield_spread"), inputs.get("yield_direction", "stable"))
    s_credit = _score_credit(inputs.get("credit_direction", "stable"))
    s_vix = _score_vix(inputs.get("vix_value"), inputs.get("vix_level", "normal"))
    s_sector = _score_sector(inputs.get("sector_rotation", "mixed"))
    s_dollar = _score_dollar(inputs.get("dollar_strength", "stable"))

    # 가중합산
    phases = ["recovery", "expansion", "overheating", "contraction"]
    final_scores = {}
    for phase in phases:
        final_scores[phase] = round(
            s_yield[phase] * weights["yield"]
            + s_credit[phase] * weights["credit"]
            + s_vix[phase] * weights["vix"]
            + s_sector[phase] * weights["sector"]
            + s_dollar[phase] * weights["dollar"],
            4,
        )

    # 최고 점수 국면
    sorted_phases = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    top_phase = sorted_phases[0][0]
    top_score = sorted_phases[0][1]
    second_score = sorted_phases[1][1] if len(sorted_phases) > 1 else 0

    # 신뢰도: (1위 - 2위) * 200, 최대 100
    confidence = min(100, round((top_score - second_score) * 200))

    phase_info = CYCLE_PHASES[top_phase]

    return {
        "phase": top_phase,
        "label": phase_info["label"],
        "description": phase_info["desc"],
        "confidence": confidence,
        "scores": {p: round(s, 3) for p, s in final_scores.items()},
        "leader_sectors": LEADER_SECTORS[top_phase],
        "inputs_summary": {
            "yield_spread": inputs.get("yield_spread"),
            "yield_direction": inputs.get("yield_direction"),
            "credit_direction": inputs.get("credit_direction"),
            "vix_value": inputs.get("vix_value"),
            "vix_level": inputs.get("vix_level"),
            "sector_rotation": inputs.get("sector_rotation"),
            "dollar_strength": inputs.get("dollar_strength"),
        },
    }

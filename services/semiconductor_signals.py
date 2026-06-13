"""반도체 사이클 신호 평가 엔진.

개별 5종 + 종합 1종. 평가 결과 dict shape (확정):
    {
        "level": "INFO" | "WARNING" | "ALERT" | "GREEN" | "YELLOW" | "RED",
        "value": float | None,
        "label": str,         # 표시명
        "threshold": dict,    # 임계값 메타
        "recent_4": list,     # 직전 4관측 [{observed_at, value}]
        "reason": str,
    }

종합 RED 임시 규칙 (Phase 1, 사용자 확정):
    capex.level ∈ (WARNING,ALERT) AND
    (memory_inventory.level == WARNING OR market_breadth.level == WARNING) → RED
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

INDICATOR_LABELS = {
    "hyperscaler_capex": "하이퍼스케일러 캐펙스 (4사 분기 YoY)",
    "memory_inventory": "메모리 재고일수 (삼성/SK 평균)",
    "hbm_contracts": "HBM 공시",
    "ai_ipo": "AI IPO",
    "market_breadth": "KOSPI 시장폭",
    "composite": "반도체 종합 신호",
}


def _recent_4(history: list[dict]) -> list[dict]:
    """ASC 정렬된 history → 마지막 4개."""
    if not history:
        return []
    return [
        {"observed_at": r.get("observed_at"), "value": r.get("value")}
        for r in history[-4:]
    ]


def _values_only(history: list[dict]) -> list[Optional[float]]:
    return [r.get("value") for r in history]


# ── 지표 2 — 하이퍼스케일러 캐펙스 ────────────────────────────


def evaluate_hyperscaler_capex(thresholds: dict, history: list[dict]) -> dict:
    """최근 8분기 YoY 기반 평가.

    - 직전 분기 YoY ≤ alert_pct → ALERT
    - 최근 2분기 YoY 모두 ≤ warning_pct → WARNING
    - 그 외 INFO
    """
    warning_pct = float(thresholds.get("yoy_warning_pct", -5.0))
    alert_pct = float(thresholds.get("yoy_alert_pct", -15.0))

    # history[-8:] 의 value_meta.yoy_pct 추출
    yoy_seq = []
    for r in history[-8:]:
        meta = r.get("value_meta") or {}
        yoy = meta.get("yoy_pct")
        if isinstance(yoy, (int, float)):
            yoy_seq.append(float(yoy))

    level = "INFO"
    reason = "관측 부족"
    if yoy_seq:
        latest = yoy_seq[-1]
        if latest <= alert_pct:
            level = "ALERT"
            reason = f"직전 분기 YoY {latest:.1f}% ≤ {alert_pct}%"
        elif (
            len(yoy_seq) >= 2
            and yoy_seq[-1] <= warning_pct
            and yoy_seq[-2] <= warning_pct
        ):
            level = "WARNING"
            reason = f"2분기 연속 YoY ≤ {warning_pct}% ({yoy_seq[-2]:.1f}/{yoy_seq[-1]:.1f}%)"
        else:
            reason = f"최근 YoY {latest:.1f}% — 임계 초과 없음"

    return {
        "level": level,
        "value": history[-1].get("value") if history else None,
        "label": INDICATOR_LABELS["hyperscaler_capex"],
        "threshold": {
            "yoy_warning_pct": warning_pct,
            "yoy_alert_pct": alert_pct,
        },
        "recent_4": _recent_4(history),
        "yoy_recent_4": yoy_seq[-4:],
        "reason": reason,
    }


# ── 지표 4 — 메모리 재고일수 ──────────────────────────────────


def evaluate_memory_inventory(thresholds: dict, history: list[dict]) -> dict:
    """- 절대 ≥ alert_threshold → ALERT
    - N분기 연속 증가 → WARNING
    """
    warning_qtr = int(thresholds.get("days_warning_increase_qtr", 2))
    alert_th = float(thresholds.get("days_alert_threshold", 120.0))

    vals = [r.get("value") for r in history if isinstance(r.get("value"), (int, float))]
    level = "INFO"
    reason = "관측 부족"
    if vals:
        latest = vals[-1]
        if latest >= alert_th:
            level = "ALERT"
            reason = f"재고일수 {latest:.1f}일 ≥ {alert_th}일"
        else:
            # 연속 증가 카운팅 (warning_qtr 회 연속)
            window = vals[-(warning_qtr + 1):]
            if len(window) >= warning_qtr + 1 and all(
                window[i] > window[i - 1] for i in range(1, len(window))
            ):
                level = "WARNING"
                trail = "/".join(f"{v:.1f}" for v in window)
                reason = f"{warning_qtr}분기 연속 증가: {trail}"
            else:
                reason = f"현재 {latest:.1f}일 — 임계 미만"

    return {
        "level": level,
        "value": history[-1].get("value") if history else None,
        "label": INDICATOR_LABELS["memory_inventory"],
        "threshold": {
            "days_warning_increase_qtr": warning_qtr,
            "days_alert_threshold": alert_th,
        },
        "recent_4": _recent_4(history),
        "reason": reason,
    }


# ── 지표 5 — HBM 공시 ────────────────────────────────────────


def evaluate_hbm_contracts(thresholds: dict, history: list[dict]) -> dict:
    """당일 매칭 count ≥ 1 → INFO (긍정 신호)."""
    latest = history[-1] if history else None
    today_count = (latest or {}).get("value") or 0

    level = "INFO" if today_count and today_count >= 1 else "GREEN"
    reason = (
        f"오늘 매칭 {int(today_count)}건"
        if today_count
        else "오늘 매칭 0건"
    )
    return {
        "level": level,
        "value": today_count,
        "label": INDICATOR_LABELS["hbm_contracts"],
        "threshold": {"keyword_regex": thresholds.get("keyword_regex", "")},
        "recent_4": _recent_4(history),
        "items": ((latest or {}).get("value_meta") or {}).get("items", []),
        "reason": reason,
    }


# ── 지표 6 — AI IPO ──────────────────────────────────────────


def evaluate_ai_ipo(thresholds: dict, per_ticker: dict) -> dict:
    """티커별 최악 등급 채택.

    per_ticker: {ticker: {history: [...]}}
    """
    loss_warn = float(thresholds.get("loss_pct_warning", -20.0))
    lockup_dminus = int(thresholds.get("lockup_dminus_days", 7))

    levels = []
    details = {}
    for ticker, payload in (per_ticker or {}).items():
        history = payload.get("history") or []
        latest = history[-1] if history else None
        if latest is None:
            continue
        ret = latest.get("value")
        meta = latest.get("value_meta") or {}
        dminus = meta.get("dminus_days")

        t_level = "GREEN"
        t_reason = "정상"
        if isinstance(ret, (int, float)) and ret <= loss_warn:
            t_level = "WARNING"
            t_reason = f"수익률 {ret:.1f}% ≤ {loss_warn}%"
        if isinstance(dminus, int) and 0 <= dminus <= lockup_dminus:
            # INFO 신호: 락업 임박
            if t_level == "GREEN":
                t_level = "INFO"
            t_reason += f"; 락업 D-{dminus}"
        details[ticker] = {
            "level": t_level,
            "return_pct": ret,
            "dminus": dminus,
            "current_price": meta.get("current_price"),
            "ipo_price": meta.get("ipo_price"),
            "reason": t_reason,
        }
        levels.append(t_level)

    # 최악 등급
    priority = {"ALERT": 3, "WARNING": 2, "INFO": 1, "GREEN": 0}
    overall = "GREEN"
    for lvl in levels:
        if priority.get(lvl, 0) > priority.get(overall, 0):
            overall = lvl

    return {
        "level": overall,
        "value": None,
        "label": INDICATOR_LABELS["ai_ipo"],
        "threshold": {
            "loss_pct_warning": loss_warn,
            "lockup_dminus_days": lockup_dminus,
        },
        "recent_4": [],
        "details": details,
        "reason": (
            f"{len(details)} 티커 평가 — 최악 등급 {overall}"
            if details else "추적 종목 없음"
        ),
    }


# ── 지표 8 — 시장폭 ──────────────────────────────────────────


def evaluate_market_breadth(
    thresholds: dict,
    adr_history: list[dict],
    concentration_history: list[dict],
) -> dict:
    """KOSPI 252일 신고 + ADR(20) < adr20_warning → WARNING.
    집중도 신고치 → INFO.
    """
    adr20_warning = float(thresholds.get("adr20_warning", 0.8))

    level = "GREEN"
    reasons = []

    latest_adr = adr_history[-1] if adr_history else None
    adr_val = (latest_adr or {}).get("value")
    adr_meta = (latest_adr or {}).get("value_meta") or {}
    is_kospi_high = bool(adr_meta.get("is_kospi_252d_high"))

    if (
        is_kospi_high
        and isinstance(adr_val, (int, float))
        and adr_val < adr20_warning
    ):
        level = "WARNING"
        reasons.append(
            f"KOSPI 252일 신고가 + ADR(20) {adr_val:.2f} < {adr20_warning}"
        )

    latest_conc = concentration_history[-1] if concentration_history else None
    conc_val = (latest_conc or {}).get("value")
    conc_meta = (latest_conc or {}).get("value_meta") or {}
    if conc_meta.get("is_252d_high") and level == "GREEN":
        level = "INFO"
        reasons.append("삼성+SK 시총 집중도 252일 신고치 경신")

    if not reasons:
        reasons.append("ADR/집중도 임계 미달")

    return {
        "level": level,
        "value": adr_val,
        "label": INDICATOR_LABELS["market_breadth"],
        "threshold": {"adr20_warning": adr20_warning},
        "recent_4": _recent_4(adr_history),
        "concentration": conc_val,
        "concentration_meta": conc_meta,
        "is_kospi_252d_high": is_kospi_high,
        "reason": " / ".join(reasons),
    }


# ── 종합 신호 (Phase 1 임시 규칙) ─────────────────────────────


def evaluate_composite(per_indicator: dict) -> dict:
    """Phase 1 임시 RED 규칙 (사용자 확정):

      capex.level ∈ (WARNING,ALERT) AND (
        memory_inventory.level == WARNING OR
        market_breadth.level == WARNING
      )  → RED
      그 외 WARNING/ALERT 1개 이상 → YELLOW
      모두 GREEN/INFO → GREEN
    """
    capex_level = (per_indicator.get("hyperscaler_capex") or {}).get("level", "INFO")
    inv_level = (per_indicator.get("memory_inventory") or {}).get("level", "INFO")
    mb_level = (per_indicator.get("market_breadth") or {}).get("level", "INFO")

    red = capex_level in ("WARNING", "ALERT") and (
        inv_level == "WARNING" or mb_level == "WARNING"
    )

    if red:
        composite_level = "RED"
        reason = (
            f"capex {capex_level} + "
            f"({'재고 WARNING' if inv_level == 'WARNING' else ''}"
            f"{' + ' if (inv_level == 'WARNING' and mb_level == 'WARNING') else ''}"
            f"{'시장폭 WARNING' if mb_level == 'WARNING' else ''})"
        )
    else:
        any_warn = any(
            (v or {}).get("level") in ("WARNING", "ALERT")
            for v in per_indicator.values()
        )
        composite_level = "YELLOW" if any_warn else "GREEN"
        if any_warn:
            warned = [
                INDICATOR_LABELS.get(k, k)
                for k, v in per_indicator.items()
                if (v or {}).get("level") in ("WARNING", "ALERT")
            ]
            reason = f"경고 지표: {', '.join(warned)}"
        else:
            reason = "전 지표 정상"

    return {
        "level": composite_level,
        "label": INDICATOR_LABELS["composite"],
        "reason": reason,
        "per_indicator_levels": {
            k: (v or {}).get("level") for k, v in per_indicator.items()
        },
        "phase1_temporary_rule": True,
        "phase1_missing_indicators": ["semiconductor_price (지표 1)", "guidance (지표 3)"],
    }


# ── 메시지 포맷 ──────────────────────────────────────────────


def format_indicator_message(
    indicator_name: str,
    prev_level: str,
    eval_result: dict,
) -> str:
    """`"[반도체] {label} {prev}→{new} | 현재 {value}{unit} (임계 {th}) | 추세: {r4}"`."""
    label = eval_result.get("label", indicator_name)
    new_level = eval_result.get("level", "INFO")
    value = eval_result.get("value")
    th = eval_result.get("threshold") or {}
    recent4 = eval_result.get("recent_4") or []
    r4_str = "/".join(
        f"{r.get('value'):.1f}" if isinstance(r.get("value"), (int, float)) else "-"
        for r in recent4
    )
    val_str = f"{value:.2f}" if isinstance(value, (int, float)) else "-"
    th_str = ", ".join(f"{k}={v}" for k, v in th.items())
    return (
        f"[반도체] {label} {prev_level}→{new_level} | "
        f"현재 {val_str} (임계 {th_str}) | 추세: {r4_str}"
    )


def format_composite_message(prev_level: str, eval_result: dict) -> str:
    new_level = eval_result.get("level", "GREEN")
    reason = eval_result.get("reason", "")
    return f"[반도체 종합] {prev_level}→{new_level} | {reason}"

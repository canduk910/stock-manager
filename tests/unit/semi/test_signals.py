"""Signal Engine 단위 테스트 — 6 평가 (개별 5 + 종합 1)."""

import pytest

from services import semiconductor_signals as sig


# ── capex ──────────────────────────────────────────────────


def test_capex_warning_two_consecutive_below_threshold():
    th = {"yoy_warning_pct": -5.0, "yoy_alert_pct": -15.0}
    history = [
        {"observed_at": "2024-12-31", "value": 50, "value_meta": {"yoy_pct": -2.0}},
        {"observed_at": "2025-03-31", "value": 50, "value_meta": {"yoy_pct": -4.0}},
        {"observed_at": "2025-06-30", "value": 48, "value_meta": {"yoy_pct": -7.0}},
        {"observed_at": "2025-09-30", "value": 47, "value_meta": {"yoy_pct": -8.2}},
    ]
    r = sig.evaluate_hyperscaler_capex(th, history)
    assert r["level"] == "WARNING"
    assert "2분기 연속" in r["reason"]


def test_capex_alert_single_quarter_deep_decline():
    th = {"yoy_warning_pct": -5.0, "yoy_alert_pct": -15.0}
    history = [
        {"observed_at": "2025-09-30", "value": 40, "value_meta": {"yoy_pct": -16.0}},
    ]
    r = sig.evaluate_hyperscaler_capex(th, history)
    assert r["level"] == "ALERT"


def test_capex_info_when_within_threshold():
    th = {"yoy_warning_pct": -5.0, "yoy_alert_pct": -15.0}
    history = [
        {"observed_at": "2025-09-30", "value": 50, "value_meta": {"yoy_pct": 12.0}},
    ]
    r = sig.evaluate_hyperscaler_capex(th, history)
    assert r["level"] == "INFO"


# ── memory inventory ──────────────────────────────────────


def test_memory_inventory_warning_three_consecutive_increases():
    th = {"days_warning_increase_qtr": 2, "days_alert_threshold": 120.0}
    history = [
        {"observed_at": "2024-12-31", "value": 75.0},
        {"observed_at": "2025-03-31", "value": 80.0},
        {"observed_at": "2025-06-30", "value": 85.0},
        {"observed_at": "2025-09-30", "value": 92.3},
    ]
    r = sig.evaluate_memory_inventory(th, history)
    assert r["level"] == "WARNING"
    assert "연속 증가" in r["reason"]


def test_memory_inventory_alert_when_absolute_threshold_breached():
    th = {"days_warning_increase_qtr": 2, "days_alert_threshold": 120.0}
    history = [
        {"observed_at": "2025-09-30", "value": 125.0},
    ]
    r = sig.evaluate_memory_inventory(th, history)
    assert r["level"] == "ALERT"


def test_memory_inventory_info_otherwise():
    th = {"days_warning_increase_qtr": 2, "days_alert_threshold": 120.0}
    history = [
        {"observed_at": "2025-06-30", "value": 80.0},
        {"observed_at": "2025-09-30", "value": 78.0},
    ]
    r = sig.evaluate_memory_inventory(th, history)
    assert r["level"] == "INFO"


# ── HBM contracts ─────────────────────────────────────────


def test_hbm_info_when_matches_today():
    history = [
        {"observed_at": "2026-06-13", "value": 2.0, "value_meta": {"items": [{}, {}]}},
    ]
    r = sig.evaluate_hbm_contracts({}, history)
    assert r["level"] == "INFO"
    assert r["value"] == 2.0


def test_hbm_green_when_zero():
    history = [{"observed_at": "2026-06-13", "value": 0.0, "value_meta": {}}]
    r = sig.evaluate_hbm_contracts({}, history)
    assert r["level"] == "GREEN"


# ── AI IPO ────────────────────────────────────────────────


def test_ai_ipo_warning_when_loss_below_threshold():
    th = {"loss_pct_warning": -20.0, "lockup_dminus_days": 7}
    per_ticker = {
        "ARM": {
            "history": [
                {"observed_at": "2026-06-13", "value": -24.0, "value_meta": {}}
            ]
        }
    }
    r = sig.evaluate_ai_ipo(th, per_ticker)
    assert r["level"] == "WARNING"
    assert r["details"]["ARM"]["level"] == "WARNING"


def test_ai_ipo_info_on_lockup_imminent_alone():
    th = {"loss_pct_warning": -20.0, "lockup_dminus_days": 7}
    per_ticker = {
        "RDDT": {
            "history": [
                {
                    "observed_at": "2026-06-13",
                    "value": 5.0,
                    "value_meta": {"dminus_days": 5},
                }
            ]
        }
    }
    r = sig.evaluate_ai_ipo(th, per_ticker)
    assert r["level"] == "INFO"


def test_ai_ipo_worst_level_aggregation():
    th = {"loss_pct_warning": -20.0, "lockup_dminus_days": 7}
    per_ticker = {
        "ARM": {
            "history": [{"observed_at": "2026-06-13", "value": -24.0, "value_meta": {}}]
        },
        "RDDT": {
            "history": [{"observed_at": "2026-06-13", "value": 10.0, "value_meta": {}}]
        },
    }
    r = sig.evaluate_ai_ipo(th, per_ticker)
    assert r["level"] == "WARNING"  # 최악 등급 채택


# ── market breadth ────────────────────────────────────────


def test_market_breadth_warning_on_high_kospi_low_adr():
    th = {"adr20_warning": 0.8}
    adr_h = [
        {
            "observed_at": "2026-06-13",
            "value": 0.72,
            "value_meta": {"is_kospi_252d_high": True},
        }
    ]
    conc_h = [
        {
            "observed_at": "2026-06-13",
            "value": 0.35,
            "value_meta": {"is_252d_high": False},
        }
    ]
    r = sig.evaluate_market_breadth(th, adr_h, conc_h)
    assert r["level"] == "WARNING"


def test_market_breadth_info_on_concentration_high_only():
    th = {"adr20_warning": 0.8}
    adr_h = [
        {
            "observed_at": "2026-06-13",
            "value": 1.05,
            "value_meta": {"is_kospi_252d_high": False},
        }
    ]
    conc_h = [
        {
            "observed_at": "2026-06-13",
            "value": 0.45,
            "value_meta": {"is_252d_high": True},
        }
    ]
    r = sig.evaluate_market_breadth(th, adr_h, conc_h)
    assert r["level"] == "INFO"


def test_market_breadth_green_default():
    th = {"adr20_warning": 0.8}
    r = sig.evaluate_market_breadth(th, [], [])
    assert r["level"] == "GREEN"


# ── composite ────────────────────────────────────────────


def test_composite_red_rule_capex_warning_plus_inventory_warning():
    per = {
        "hyperscaler_capex": {"level": "WARNING"},
        "memory_inventory": {"level": "WARNING"},
        "market_breadth": {"level": "GREEN"},
        "hbm_contracts": {"level": "GREEN"},
        "ai_ipo": {"level": "GREEN"},
    }
    r = sig.evaluate_composite(per)
    assert r["level"] == "RED"
    assert "capex" in r["reason"]


def test_composite_red_rule_capex_warning_plus_market_breadth_warning():
    per = {
        "hyperscaler_capex": {"level": "ALERT"},
        "memory_inventory": {"level": "GREEN"},
        "market_breadth": {"level": "WARNING"},
        "hbm_contracts": {"level": "GREEN"},
        "ai_ipo": {"level": "GREEN"},
    }
    r = sig.evaluate_composite(per)
    assert r["level"] == "RED"


def test_composite_yellow_when_only_one_warning():
    per = {
        "hyperscaler_capex": {"level": "GREEN"},
        "memory_inventory": {"level": "WARNING"},
        "market_breadth": {"level": "GREEN"},
        "hbm_contracts": {"level": "GREEN"},
        "ai_ipo": {"level": "GREEN"},
    }
    r = sig.evaluate_composite(per)
    assert r["level"] == "YELLOW"


def test_composite_green_when_all_normal():
    per = {
        "hyperscaler_capex": {"level": "INFO"},
        "memory_inventory": {"level": "INFO"},
        "market_breadth": {"level": "GREEN"},
        "hbm_contracts": {"level": "GREEN"},
        "ai_ipo": {"level": "GREEN"},
    }
    r = sig.evaluate_composite(per)
    assert r["level"] == "GREEN"
    assert r["phase1_temporary_rule"] is True


# ── 메시지 포맷 ─────────────────────────────────────────


def test_message_format_individual():
    eval_result = {
        "label": "메모리 재고일수 (삼성/SK 평균)",
        "level": "WARNING",
        "value": 92.3,
        "threshold": {"days_alert_threshold": 120.0},
        "recent_4": [
            {"observed_at": "2024-12-31", "value": 78.1},
            {"observed_at": "2025-03-31", "value": 82.0},
            {"observed_at": "2025-06-30", "value": 87.4},
            {"observed_at": "2025-09-30", "value": 92.3},
        ],
    }
    msg = sig.format_indicator_message("memory_inventory", "GREEN", eval_result)
    assert "[반도체]" in msg
    assert "GREEN→WARNING" in msg
    assert "78.1/82.0/87.4/92.3" in msg


def test_message_format_composite():
    msg = sig.format_composite_message(
        "YELLOW",
        {"level": "RED", "reason": "capex WARNING + 재고 WARNING"},
    )
    assert msg == "[반도체 종합] YELLOW→RED | capex WARNING + 재고 WARNING"

"""REQ-FH-EXT-SERVICE-01: fetch_foreign_holding 확장 단위 테스트.

V1.5 → V1.6 확장:
- 기본값 days=120, 범위 5~180
- 누적 캐시 키 `foreign_holding:daily_history:{code}` 사용
- change_alert 객체 (3%p 임계)
- daily_history_total_days
- daily 응답에서 누적 row의 hts_frgn_ehrt None 제외
- V1.5 회귀 가드 (days=30 / advisory_note / 매매 액션 키 부재)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, ServiceError,
)


# ── 공용 fixture ──────────────────────────────────────────────────────────────

def _snapshot(*, frgn_qty: int | None = 3223990000,
              ehrt: float | None = 54.00, lstn: int = 5970240000) -> dict:
    return {
        "code": "005930",
        "lstn_stcn": lstn,
        "frgn_hldn_qty": frgn_qty,
        "hts_frgn_ehrt": ehrt,
        "as_of_date": "2026-05-12",
    }


def _daily(n: int = 30, start_ehrt: float = 53.85, step: float = 0.005,
           start_date: str = "2026-04-13") -> list[dict]:
    """KIS 30일 응답 모킹. date는 ascending."""
    import datetime as _dt
    base = _dt.date.fromisoformat(start_date)
    out = []
    for i in range(n):
        out.append({
            "date": (base + _dt.timedelta(days=i)).isoformat(),
            "close": 71000 + i * 100,
            "hts_frgn_ehrt": start_ehrt + i * step,
            "frgn_ntby_qty": 100000 + i * 1000,
        })
    return out


@pytest.fixture(autouse=True)
def _kis_keys_set(monkeypatch):
    monkeypatch.setattr("services.supply_demand_service.KIS_APP_KEY", "K", raising=False)
    monkeypatch.setattr("services.supply_demand_service.KIS_APP_SECRET", "S", raising=False)


@pytest.fixture(autouse=True)
def _isolated_cache(monkeypatch):
    """macro_store에 대한 in-memory 모의 (카테고리별 독립 저장)."""
    state = {}

    def _get(cat):
        return state.get(cat)

    def _save(cat, val):
        state[cat] = val

    def _delete(cat):
        state.pop(cat, None)

    monkeypatch.setattr("services.supply_demand_service.macro_store.get_today", _get)
    monkeypatch.setattr("services.supply_demand_service.macro_store.save_today", _save)
    monkeypatch.setattr("services.supply_demand_service.macro_store.delete_today", _delete)
    return state


# ── 입력 검증 ─────────────────────────────────────────────────────────────────

class TestExtendedValidation:

    def test_default_days_is_120(self):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930")
        assert result["days"] == 120

    def test_days_below_5_raises(self):
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ServiceError):
            fetch_foreign_holding("005930", 4)

    def test_days_above_180_raises(self):
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ServiceError):
            fetch_foreign_holding("005930", 181)

    def test_days_180_allowed(self):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930", 180)
        assert result["days"] == 180

    def test_non_domestic_still_raises(self):
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ServiceError):
            fetch_foreign_holding("AAPL", 120)

    def test_v15_regression_days_30_works(self):
        """V1.5 호환 회귀: days=30 호출 정상."""
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930", 30)
        assert result["days"] == 30
        assert "advisory_note" in result
        assert "snapshot" in result and "daily" in result


# ── 누적 캐시 ─────────────────────────────────────────────────────────────────

class TestAccumulationCache:

    def test_first_call_stores_history(self, _isolated_cache):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            fetch_foreign_holding("005930", 120)
        # 누적 + V1.5 30일 캐시 양쪽 저장
        assert "foreign_holding:daily_history:005930" in _isolated_cache
        assert "foreign_holding:daily:005930" in _isolated_cache
        history = _isolated_cache["foreign_holding:daily_history:005930"]
        assert len(history) == 30

    def test_history_appends_new_days_only(self, _isolated_cache):
        """누적 캐시 240건 + KIS 신규 30건(겹침 10) → 260건 → 250 cap."""
        from services.supply_demand_service import fetch_foreign_holding
        # 사전 적재: 240건 (2025-09-01 ~ 2026-04-27 등 순차 가짜 일자)
        import datetime as _dt
        base = _dt.date(2025, 9, 1)
        existing = [{
            "date": (base + _dt.timedelta(days=i)).isoformat(),
            "close": 71000 + i,
            "hts_frgn_ehrt": 50.0 + i * 0.01,
            "frgn_ntby_qty": 1000,
        } for i in range(240)]
        _isolated_cache["foreign_holding:daily_history:005930"] = existing

        # 새 30건: 마지막 10건은 기존과 중복, 20건은 신규
        last_existing_date = _dt.date.fromisoformat(existing[-10]["date"])
        new = [{
            "date": (last_existing_date + _dt.timedelta(days=i)).isoformat(),
            "close": 72000 + i,
            "hts_frgn_ehrt": 53.0 + i * 0.02,
            "frgn_ntby_qty": 2000,
        } for i in range(30)]

        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=new):
            fetch_foreign_holding("005930", 120)

        history = _isolated_cache["foreign_holding:daily_history:005930"]
        assert len(history) == 250  # FIFO cap
        # ascending sorted
        dates = [r["date"] for r in history]
        assert dates == sorted(dates)


# ── change_alert ────────────────────────────────────────────────────────────

class TestChangeAlert:

    def test_change_alert_breached_when_above_threshold(self):
        from services.supply_demand_service import fetch_foreign_holding
        # daily 슬라이스에서 첫=50.0 / 끝=54.0 → +4.0%p > 3.0 → breached
        rows = [
            {"date": "2026-01-01", "close": 70000, "hts_frgn_ehrt": 50.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-02", "close": 70100, "hts_frgn_ehrt": 51.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-03", "close": 70200, "hts_frgn_ehrt": 52.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-04", "close": 70300, "hts_frgn_ehrt": 53.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-05", "close": 70400, "hts_frgn_ehrt": 54.0, "frgn_ntby_qty": 0},
        ]
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=rows):
            result = fetch_foreign_holding("005930", 5)
        ca = result.get("change_alert")
        assert ca is not None
        assert ca["breached"] is True
        assert abs(ca["abs_change_pct_point"] - 4.0) < 0.001
        assert ca["signed_change_pct_point"] > 0
        assert ca["threshold_pct_point"] == 3.0
        assert ca["color"] == "warning"
        assert ca["first_date"] == "2026-01-01"
        assert ca["last_date"] == "2026-01-05"

    def test_change_alert_not_breached_under_threshold(self):
        from services.supply_demand_service import fetch_foreign_holding
        # +1.5%p
        rows = [
            {"date": "2026-01-01", "close": 70000, "hts_frgn_ehrt": 50.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-02", "close": 70100, "hts_frgn_ehrt": 51.5, "frgn_ntby_qty": 0},
        ]
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=rows):
            result = fetch_foreign_holding("005930", 5)
        ca = result.get("change_alert")
        assert ca is not None
        assert ca["breached"] is False
        assert ca["color"] == "neutral"

    def test_change_alert_breached_when_decrease_below_threshold(self):
        """음수 변화 -3.5%p → abs=3.5 >= 3.0 → breached, signed 음수."""
        from services.supply_demand_service import fetch_foreign_holding
        rows = [
            {"date": "2026-01-01", "close": 70000, "hts_frgn_ehrt": 55.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-02", "close": 70100, "hts_frgn_ehrt": 51.5, "frgn_ntby_qty": 0},
        ]
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=rows):
            result = fetch_foreign_holding("005930", 5)
        ca = result.get("change_alert")
        assert ca["breached"] is True
        assert ca["signed_change_pct_point"] < 0
        assert abs(ca["abs_change_pct_point"] - 3.5) < 0.001

    def test_change_alert_boundary_3pct_breached(self):
        """경계값 정확히 +3.0%p → breached(abs >= threshold)."""
        from services.supply_demand_service import fetch_foreign_holding
        rows = [
            {"date": "2026-01-01", "close": 70000, "hts_frgn_ehrt": 50.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-02", "close": 70100, "hts_frgn_ehrt": 53.0, "frgn_ntby_qty": 0},
        ]
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=rows):
            result = fetch_foreign_holding("005930", 5)
        ca = result.get("change_alert")
        assert ca["breached"] is True

    def test_change_alert_boundary_just_under_threshold(self):
        from services.supply_demand_service import fetch_foreign_holding
        rows = [
            {"date": "2026-01-01", "close": 70000, "hts_frgn_ehrt": 50.0, "frgn_ntby_qty": 0},
            {"date": "2026-01-02", "close": 70100, "hts_frgn_ehrt": 52.99, "frgn_ntby_qty": 0},
        ]
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=rows):
            result = fetch_foreign_holding("005930", 5)
        ca = result.get("change_alert")
        assert ca["breached"] is False

    def test_change_alert_omitted_when_single_row(self):
        """단일 row(첫=끝) → change_alert 키 부재 또는 None."""
        from services.supply_demand_service import fetch_foreign_holding
        rows = [
            {"date": "2026-01-01", "close": 70000, "hts_frgn_ehrt": 50.0, "frgn_ntby_qty": 0},
        ]
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=rows):
            result = fetch_foreign_holding("005930", 5)
        # 객체 부재 또는 None (둘 다 UI에서 안전)
        ca = result.get("change_alert")
        assert ca is None or ("breached" in ca and ca.get("first_date") == ca.get("last_date"))


# ── daily_history_total_days ──────────────────────────────────────────────────

class TestHistoryTotalDays:

    def test_first_call_30_days_returns_30(self):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930", 120)
        assert result.get("daily_history_total_days") == 30

    def test_after_accumulation(self, _isolated_cache):
        import datetime as _dt
        base = _dt.date(2025, 11, 1)
        existing = [{
            "date": (base + _dt.timedelta(days=i)).isoformat(),
            "close": 71000 + i,
            "hts_frgn_ehrt": 50.0 + i * 0.01,
            "frgn_ntby_qty": 1000,
        } for i in range(100)]
        _isolated_cache["foreign_holding:daily_history:005930"] = existing

        # KIS는 마지막 30일 (기존과 일부 겹침)
        last_existing_date = _dt.date.fromisoformat(existing[-10]["date"])
        new = [{
            "date": (last_existing_date + _dt.timedelta(days=i)).isoformat(),
            "close": 72000 + i,
            "hts_frgn_ehrt": 51.0 + i * 0.02,
            "frgn_ntby_qty": 2000,
        } for i in range(30)]

        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=new):
            result = fetch_foreign_holding("005930", 120)
        # 100 existing + 20 new (10 겹침) = 120
        assert result["daily_history_total_days"] == 120


# ── daily 슬라이스 + None ehrt 필터링 ────────────────────────────────────────

class TestDailySlicing:

    def test_daily_sliced_to_requested_days(self, _isolated_cache):
        """누적 200일 + days=120 → daily 길이 120."""
        import datetime as _dt
        base = _dt.date(2025, 11, 1)
        existing = [{
            "date": (base + _dt.timedelta(days=i)).isoformat(),
            "close": 71000,
            "hts_frgn_ehrt": 50.0 + i * 0.01,
            "frgn_ntby_qty": 1000,
        } for i in range(200)]
        _isolated_cache["foreign_holding:daily_history:005930"] = existing

        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930", 120)
        assert len(result["daily"]) == 120

    def test_daily_excludes_none_ehrt_rows(self, _isolated_cache):
        """누적에 None ehrt row가 포함되어도 daily 응답에서 제외."""
        import datetime as _dt
        base = _dt.date(2026, 4, 1)
        existing = [
            {"date": (base + _dt.timedelta(days=i)).isoformat(),
             "close": 71000, "hts_frgn_ehrt": (None if i == 5 else 50.0 + i * 0.01),
             "frgn_ntby_qty": 1000}
            for i in range(30)
        ]
        _isolated_cache["foreign_holding:daily_history:005930"] = existing

        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30, start_date=(base + _dt.timedelta(days=30)).isoformat())):
            result = fetch_foreign_holding("005930", 60)
        # daily 응답에 frgn_ehrt_pct=None row 없음
        for d in result["daily"]:
            assert d["frgn_ehrt_pct"] is not None


# ── 회귀 가드 ────────────────────────────────────────────────────────────────

class TestRegressionV15:

    def test_no_trade_action_keys_top_level(self):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930", 120)
        for forbidden in ("recommendation", "action", "buy_signal", "trade_signal", "signal"):
            assert forbidden not in result

    def test_advisory_note_present(self):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_daily(30)):
            result = fetch_foreign_holding("005930", 120)
        assert "advisory_note" in result
        assert "한도소진율" in result["advisory_note"]

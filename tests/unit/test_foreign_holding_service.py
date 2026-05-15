"""services/supply_demand_service.fetch_foreign_holding 단위 테스트.

REQ-FH-SERVICE-01 + REQ-FH-CACHE-01 수용 기준.

- 응답 shape (snapshot/daily/advisory_note/color_map)
- 한도수량 도출/None 폴백/exceeded
- limit_status 임계값(50/80/95)
- 매매 액션 키 부재
- macro_store 일자 캐시 (적중/저장/결함 가드)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, ServiceError,
)


# ── 공용 fixture ──────────────────────────────────────────────────────────────

def _fake_snapshot(
    *, frgn_qty: int | None = 3223990000,
    ehrt: float | None = 54.00, lstn: int = 5970240000,
) -> dict:
    return {
        "code": "005930",
        "lstn_stcn": lstn,
        "frgn_hldn_qty": frgn_qty,
        "hts_frgn_ehrt": ehrt,
        "as_of_date": "2026-05-12",
    }


def _fake_daily(n: int = 30) -> list[dict]:
    out = []
    base_close = 71000
    for i in range(n):
        out.append({
            "date": f"2026-05-{i+1:02d}",
            "close": base_close + i * 100,
            "hts_frgn_ehrt": 53.85 + i * 0.005,
            "frgn_ntby_qty": 100000 + i * 1000,
        })
    return out


@pytest.fixture(autouse=True)
def _kis_keys_set(monkeypatch):
    """KIS 키 mock — fetch_foreign_holding 진입부 ConfigError 방지."""
    monkeypatch.setattr("services.supply_demand_service.KIS_APP_KEY", "K", raising=False)
    monkeypatch.setattr("services.supply_demand_service.KIS_APP_SECRET", "S", raising=False)


@pytest.fixture(autouse=True)
def _no_cache(monkeypatch):
    """macro_store get/save/delete mock — 캐시 미스 기본."""
    state = {"snapshot": {}, "daily": {}}

    def _get(cat):
        return state["snapshot"].get(cat) or state["daily"].get(cat)

    def _save(cat, val):
        if cat.startswith("foreign_holding:snapshot"):
            state["snapshot"][cat] = val
        else:
            state["daily"][cat] = val

    def _delete(cat):
        state["snapshot"].pop(cat, None)
        state["daily"].pop(cat, None)

    monkeypatch.setattr("services.supply_demand_service.macro_store.get_today", _get)
    monkeypatch.setattr("services.supply_demand_service.macro_store.save_today", _save)
    monkeypatch.setattr("services.supply_demand_service.macro_store.delete_today", _delete)
    return state


# ── REQ-FH-SERVICE-01: 응답 shape ────────────────────────────────────────────

class TestFetchForeignHoldingShape:

    def test_returns_required_top_keys(self):
        from services.supply_demand_service import fetch_foreign_holding

        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(30)):
            result = fetch_foreign_holding("005930", 30)

        for key in ("code", "name", "days", "as_of", "color_map",
                    "advisory_note", "snapshot", "daily"):
            assert key in result, f"누락 키: {key}"
        assert result["code"] == "005930"
        assert result["days"] == 30
        assert "foreign" in result["color_map"] and "limit" in result["color_map"]

    def test_advisory_note_contains_personal_unrelated(self):
        """안전 고지: '한도소진율과 개인 투자자 매수 적합성' 문구 포함."""
        from services.supply_demand_service import fetch_foreign_holding

        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(5)):
            result = fetch_foreign_holding("005930", 5)

        note = result["advisory_note"]
        assert "한도소진율" in note
        assert "개인" in note
        assert "매매 신호" in note or "단독 사용" in note

    def test_no_trade_action_keys(self):
        """매매 액션 키(recommendation/action/buy_signal/signal) 부재."""
        from services.supply_demand_service import fetch_foreign_holding

        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(5)):
            result = fetch_foreign_holding("005930", 5)

        for forbidden in ("recommendation", "action", "buy_signal", "trade_signal", "signal"):
            assert forbidden not in result, f"금지 키: {forbidden}"
            assert forbidden not in result["snapshot"], f"snapshot 금지 키: {forbidden}"
            for d in result["daily"]:
                assert forbidden not in d, f"daily 금지 키: {forbidden}"

    def test_man_unit_conversion(self):
        """3,223,990,000주 → 322,399만주 (÷10000 반올림)."""
        from services.supply_demand_service import fetch_foreign_holding

        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(5)):
            result = fetch_foreign_holding("005930", 5)

        snap = result["snapshot"]
        assert snap["frgn_hldn_man"] == 322399
        assert snap["lstn_stcn_man"] == 597024


# ── REQ-FH-SERVICE-01: 입력 검증 + 예외 ──────────────────────────────────────

class TestFetchForeignHoldingValidation:

    def test_non_domestic_raises_service_error(self):
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ServiceError):
            fetch_foreign_holding("AAPL", 30)

    def test_days_below_min_raises(self):
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ServiceError):
            fetch_foreign_holding("005930", 3)

    def test_days_above_max_raises(self):
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ServiceError):
            fetch_foreign_holding("005930", 50)

    def test_missing_kis_raises_config(self, monkeypatch):
        monkeypatch.setattr("services.supply_demand_service.KIS_APP_KEY", "", raising=False)
        monkeypatch.setattr("services.supply_demand_service.KIS_APP_SECRET", "", raising=False)
        from services.supply_demand_service import fetch_foreign_holding
        with pytest.raises(ConfigError):
            fetch_foreign_holding("005930", 30)

    def test_not_found_propagates(self):
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   side_effect=NotFoundError("종목 999999 시세 응답 없음")):
            with pytest.raises(NotFoundError):
                fetch_foreign_holding("999999", 30)


# ── REQ-FH-SERVICE-01: 한도수량 도출 + limit_status ───────────────────────────

class TestLimitStatus:

    def _run(self, ehrt: float | None, frgn_qty: int | None = 3223990000,
             lstn: int = 5970240000) -> dict:
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot(frgn_qty=frgn_qty, ehrt=ehrt, lstn=lstn)), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(5)):
            return fetch_foreign_holding("005930", 5)["snapshot"]

    def test_unlimited_when_ehrt_none(self):
        """한도 미설정 케이스: ehrt None + frgn_qty 정상(0이 아닌 작은 값).

        결함 응답(둘 다 None)이 아닌, ETF/우선주처럼 KIS가 ehrt만 None으로 보고하는 케이스.
        """
        snap = self._run(ehrt=None, frgn_qty=10)
        assert snap["is_limit_unset"] is True
        assert snap["frgn_limit_man"] is None
        assert snap["limit_status"] == "unlimited"

    def test_unlimited_when_ehrt_below_threshold(self):
        """hts_frgn_ehrt < 0.01 → unlimited."""
        snap = self._run(ehrt=0.0)
        assert snap["limit_status"] == "unlimited"
        assert snap["frgn_limit_man"] is None
        assert snap["is_limit_unset"] is True

    def test_safe_below_50(self):
        snap = self._run(ehrt=49.99)
        assert snap["limit_status"] == "safe"

    def test_caution_at_50(self):
        snap = self._run(ehrt=50.00)
        assert snap["limit_status"] == "caution"

    def test_caution_just_below_80(self):
        snap = self._run(ehrt=79.99)
        assert snap["limit_status"] == "caution"

    def test_warning_at_80(self):
        snap = self._run(ehrt=80.00)
        assert snap["limit_status"] == "warning"

    def test_warning_just_below_95(self):
        snap = self._run(ehrt=94.99)
        assert snap["limit_status"] == "warning"

    def test_saturated_at_95(self):
        snap = self._run(ehrt=95.00)
        assert snap["limit_status"] == "saturated"

    def test_limit_quantity_derivation(self):
        """한도수량 = frgn_hldn_qty / (ehrt/100) ÷ 10000.
        3,223,990,000 / 0.54 = 5,970,351,851주 → 597,035 만주."""
        snap = self._run(ehrt=54.00, frgn_qty=3223990000)
        assert snap["frgn_limit_man"] is not None
        # 정확한 역산값 검증(반올림 허용 ±2만주)
        assert abs(snap["frgn_limit_man"] - 597035) <= 2

    def test_remaining_clipped_when_exceeded(self):
        """frgn_qty > 도출 한도 → exceeded + 잔여 0."""
        # 인위적: ehrt=100% 보고였는데 frgn_qty > lstn 시뮬레이션은 불가.
        # 대신 exceeded는 한도 < 보유로 정의됨. 정상 도출 시 한도 ≈ 보유/ehrt이므로
        # 한도 < 보유 케이스를 모사하려면 ehrt가 실제보다 작게 보고된 경우.
        # 100주 보유 + ehrt=100% → 한도=100주, exceeded 아님.
        # 100주 보유 + ehrt=200%(비현실) → 한도=50주, exceeded.
        # 현실 케이스: 한도가 외국인 한도 정책 변경으로 줄어든 직후.
        # 시뮬레이션을 위해 ehrt=200%(테스트 한정)로 강제.
        snap = self._run(ehrt=200.0, frgn_qty=1000000)
        # 한도 = 1000000 / 2.0 = 500000주 = 50만주, 보유 = 100만주 = exceeded
        assert snap["is_exceeded"] is True
        assert snap["frgn_remaining_man"] == 0
        assert snap["limit_status"] == "exceeded"


# ── REQ-FH-CACHE-01: 캐시 적중/저장 ───────────────────────────────────────────

class TestCache:

    def test_first_call_invokes_kis(self, _no_cache):
        from services.supply_demand_service import fetch_foreign_holding

        snap_mock = patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                          return_value=_fake_snapshot())
        daily_mock = patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                           return_value=_fake_daily(5))
        with snap_mock as sm, daily_mock as dm:
            fetch_foreign_holding("005930", 5)
        assert sm.call_count == 1
        assert dm.call_count == 1
        # 캐시 저장됨
        assert "foreign_holding:snapshot:005930" in _no_cache["snapshot"]
        assert "foreign_holding:daily:005930" in _no_cache["daily"]

    def test_second_call_uses_cache(self, _no_cache):
        from services.supply_demand_service import fetch_foreign_holding
        snap_mock = patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                          return_value=_fake_snapshot())
        daily_mock = patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                           return_value=_fake_daily(5))
        # 1차 호출
        with snap_mock, daily_mock:
            fetch_foreign_holding("005930", 5)
        # 2차 호출: KIS 미호출
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot") as sm, \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily") as dm:
            fetch_foreign_holding("005930", 5)
            assert sm.call_count == 0
            assert dm.call_count == 0

    def test_defective_snapshot_raises_external(self, _no_cache):
        """frgn_hldn_qty None AND hts_frgn_ehrt None → 캐시 저장 거부 + ExternalAPIError."""
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot(frgn_qty=None, ehrt=None)), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(5)):
            with pytest.raises(ExternalAPIError):
                fetch_foreign_holding("005930", 5)
        # 캐시 저장 거부
        assert "foreign_holding:snapshot:005930" not in _no_cache["snapshot"]

    def test_defective_daily_raises_external(self, _no_cache):
        """일별 전 row의 hts_frgn_ehrt가 None → ExternalAPIError."""
        bad_daily = [
            {"date": f"2026-05-{i+1:02d}", "close": 71000,
             "hts_frgn_ehrt": None, "frgn_ntby_qty": 0}
            for i in range(5)
        ]
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=bad_daily):
            with pytest.raises(ExternalAPIError):
                fetch_foreign_holding("005930", 5)


# ── REQ-FH-SERVICE-01: 일별 보유수량 역산 ───────────────────────────────────

class TestDailyEstimation:

    def test_daily_includes_estimated_man(self):
        """일별 응답에 frgn_hldn_man_estimated 포함 (한도수량 × ehrt/100 ÷ 10000)."""
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot()), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(3)):
            result = fetch_foreign_holding("005930", 5)

        assert len(result["daily"]) == 3
        first = result["daily"][0]
        for key in ("date", "close", "frgn_ehrt_pct", "frgn_ntby_qty",
                    "frgn_hldn_man_estimated"):
            assert key in first

    def test_estimated_is_none_when_unlimited(self):
        """한도 미설정 → 일별 추정값 None."""
        from services.supply_demand_service import fetch_foreign_holding
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot(frgn_qty=None, ehrt=None)), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(3)):
            with pytest.raises(ExternalAPIError):
                fetch_foreign_holding("005930", 5)
        # 결함 가드로 ExternalAPIError가 먼저 발생 — 정상 unlimited 케이스는
        # ehrt < 0.01 시 snapshot은 정상이지만 frgn_qty > 0이어야 함
        # 별도 케이스로 검증: ehrt=0.0 + frgn_qty=10 (한도 미설정 + 잡주식)
        with patch("services.supply_demand_service.wrapper_get_foreign_holding_snapshot",
                   return_value=_fake_snapshot(frgn_qty=10, ehrt=0.0)), \
             patch("services.supply_demand_service.wrapper_get_foreign_holding_daily",
                   return_value=_fake_daily(3)):
            result = fetch_foreign_holding("005930", 5)
        assert result["snapshot"]["limit_status"] == "unlimited"
        # unlimited 시 estimated는 None
        for d in result["daily"]:
            assert d["frgn_hldn_man_estimated"] is None

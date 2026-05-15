"""REQ-FH-EXT-ROUTER-01: 외국인 보유 라우터 days 범위 확장 + 기본값 테스트.

V1.5 30일 → V1.6 120일 기본값, 5~180 범위.
응답에 daily_history_total_days + change_alert 키 추가됨.
"""
from __future__ import annotations

from unittest.mock import patch

from services.exceptions import ServiceError


def _fake_v16_response(code: str = "005930", days: int = 120,
                       history_total: int = 30) -> dict:
    """V1.6 응답 (daily_history_total_days + change_alert 추가)."""
    return {
        "code": code,
        "name": "삼성전자",
        "days": days,
        "as_of": "2026-05-12",
        "color_map": {"foreign": "#3B82F6", "limit": "#9CA3AF"},
        "advisory_note": (
            "참고용 데이터입니다. 한도소진율과 개인 투자자 매수 적합성은 무관합니다(외국인 합산 한도). "
            "매매 신호로 단독 사용 금지(Graham 원칙)."
        ),
        "snapshot": {
            "lstn_stcn_man": 597024,
            "frgn_hldn_man": 322399,
            "frgn_holding_pct": 54.00,
            "frgn_ehrt_pct": 54.00,
            "frgn_limit_man": 597024,
            "frgn_remaining_man": 274625,
            "frgn_remaining_pct_of_limit": 46.00,
            "limit_status": "caution",
            "is_limit_unset": False,
            "is_exceeded": False,
        },
        "daily": [
            {"date": "2026-04-15", "close": 71000, "frgn_ehrt_pct": 53.85,
             "frgn_ntby_qty": 152000, "frgn_hldn_man_estimated": 321500},
        ],
        "daily_history_total_days": history_total,
        "change_alert": {
            "first_date": "2026-01-15",
            "first_ehrt_pct": 50.20,
            "last_date": "2026-05-12",
            "last_ehrt_pct": 54.00,
            "abs_change_pct_point": 3.80,
            "signed_change_pct_point": 3.80,
            "threshold_pct_point": 3.0,
            "breached": True,
            "color": "warning",
        },
    }


class TestExtendedRouter:

    def test_default_days_is_120(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_v16_response("005930", 120)) as svc:
            resp = client.get("/api/advisory/005930/foreign-holding")
        assert resp.status_code == 200
        call = svc.call_args
        days = call.kwargs.get("days") if call.kwargs else (
            call.args[1] if len(call.args) > 1 else None)
        assert days == 120

    def test_days_180_accepted(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_v16_response("005930", 180)) as svc:
            resp = client.get("/api/advisory/005930/foreign-holding?days=180")
        assert resp.status_code == 200
        call = svc.call_args
        days = call.kwargs.get("days") if call.kwargs else (
            call.args[1] if len(call.args) > 1 else None)
        assert days == 180

    def test_days_above_180_returns_400(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=ServiceError("days는 5~180 범위여야 합니다.")):
            resp = client.get("/api/advisory/005930/foreign-holding?days=181")
        assert resp.status_code == 400

    def test_days_below_5_returns_400(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=ServiceError("days는 5~180 범위여야 합니다.")):
            resp = client.get("/api/advisory/005930/foreign-holding?days=4")
        assert resp.status_code == 400

    def test_v15_regression_days_30_still_works(self, client):
        """V1.5 호환: days=30 호출."""
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_v16_response("005930", 30)) as svc:
            resp = client.get("/api/advisory/005930/foreign-holding?days=30")
        assert resp.status_code == 200
        body = resp.json()
        assert body["days"] == 30
        assert "advisory_note" in body

    def test_response_includes_new_v16_keys(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_v16_response("005930", 120, history_total=120)):
            resp = client.get("/api/advisory/005930/foreign-holding")
        body = resp.json()
        assert "daily_history_total_days" in body
        assert body["daily_history_total_days"] == 120
        # change_alert는 객체 (또는 부재) — fake에 포함되어 있으므로 검증
        assert "change_alert" in body
        assert body["change_alert"]["threshold_pct_point"] == 3.0

    def test_no_trade_action_keys_in_response(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_v16_response("005930", 120)):
            resp = client.get("/api/advisory/005930/foreign-holding")
        body = resp.json()
        for forbidden in ("recommendation", "action", "buy_signal", "trade_signal", "signal"):
            assert forbidden not in body
            assert forbidden not in body["snapshot"]

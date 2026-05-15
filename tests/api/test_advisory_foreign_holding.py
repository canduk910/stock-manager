"""GET /api/advisory/{code}/foreign-holding 엔드포인트 테스트.

REQ-FH-ROUTER-01.
- 200 응답 + advisory_note 존재 + snapshot/daily 구조
- 매매 액션 키(recommendation/action/buy_signal) 부재
- 해외 종목 → 400 (ServiceError)
- 미존재 → 404
- KIS 키 미설정 → 503
- KIS 5xx → 502
- days 범위 외 → 400
- days 쿼리 전달 검증
"""
from __future__ import annotations

from unittest.mock import patch

from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, ServiceError,
)


def _fake_fh_response(code: str = "005930", days: int = 30) -> dict:
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
    }


class TestForeignHoldingEndpoint:

    def test_200_response_structure(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_fh_response("005930", 30)):
            resp = client.get("/api/advisory/005930/foreign-holding")
        assert resp.status_code == 200
        body = resp.json()
        for key in ("code", "name", "days", "as_of", "color_map",
                    "advisory_note", "snapshot", "daily"):
            assert key in body
        assert body["snapshot"]["limit_status"] == "caution"

    def test_advisory_note_present(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_fh_response("005930", 30)):
            resp = client.get("/api/advisory/005930/foreign-holding")
        body = resp.json()
        assert "advisory_note" in body
        assert "한도소진율" in body["advisory_note"]

    def test_no_trade_action_keys(self, client):
        """매매 액션 키(recommendation/action/buy_signal/signal) 부재."""
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_fh_response("005930", 30)):
            resp = client.get("/api/advisory/005930/foreign-holding")
        body = resp.json()
        for forbidden in ("recommendation", "action", "buy_signal", "trade_signal", "signal"):
            assert forbidden not in body, f"매매 액션 키 금지: {forbidden}"
            assert forbidden not in body["snapshot"], f"snapshot 키 금지: {forbidden}"
            for d in body["daily"]:
                assert forbidden not in d, f"daily 키 금지: {forbidden}"

    def test_non_domestic_returns_400(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=ServiceError("국내 종목만 지원합니다.")):
            resp = client.get("/api/advisory/AAPL/foreign-holding")
        assert resp.status_code == 400

    def test_not_found_returns_404(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=NotFoundError("종목 999999 시세 응답 없음")):
            resp = client.get("/api/advisory/999999/foreign-holding")
        assert resp.status_code == 404

    def test_missing_kis_returns_503(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=ConfigError("KIS API 키 설정이 필요합니다.")):
            resp = client.get("/api/advisory/005930/foreign-holding")
        assert resp.status_code == 503

    def test_external_api_returns_502(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=ExternalAPIError("KIS down")):
            resp = client.get("/api/advisory/005930/foreign-holding")
        assert resp.status_code == 502

    def test_days_above_max_returns_400(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   side_effect=ServiceError("days는 5~30 범위여야 합니다.")):
            resp = client.get("/api/advisory/005930/foreign-holding?days=50")
        assert resp.status_code == 400

    def test_days_query_passed_through(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_fh_response("005930", 10)) as svc:
            resp = client.get("/api/advisory/005930/foreign-holding?days=10")
        assert resp.status_code == 200
        call = svc.call_args
        days = call.kwargs.get("days") if call.kwargs else (call.args[1] if len(call.args) > 1 else None)
        assert days == 10

    def test_default_days_120_v16(self, client):
        """V1.6 라우터 기본값 120 (V1.5 30 → V1.6 120 — 사용자 요구 '반년').

        days=120 명시 요청도 동일 동작 회귀 가드.
        """
        with patch("routers.advisory.supply_demand_service.fetch_foreign_holding",
                   return_value=_fake_fh_response("005930", 120)) as svc:
            resp = client.get("/api/advisory/005930/foreign-holding")
        assert resp.status_code == 200
        call = svc.call_args
        days = call.kwargs.get("days") if call.kwargs else (call.args[1] if len(call.args) > 1 else None)
        assert days == 120

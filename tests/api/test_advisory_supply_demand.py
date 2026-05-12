"""GET /api/advisory/{code}/supply-demand 엔드포인트 테스트.

REQ-SUPPLY-ROUTER-02.
- 200 응답 + advisory_note 존재
- 매매 액션 키 (recommendation/action/buy_signal) 부재
- 해외 종목 → 400 (ServiceError)
- 미존재 종목 → 404 (NotFoundError)
- KIS 키 미설정 → 503 (ConfigError)
"""
from __future__ import annotations

from unittest.mock import patch

from services.exceptions import (
    ConfigError, ExternalAPIError, NotFoundError, ServiceError,
)


def _fake_stock_response(code="005930", days=30):
    return {
        "code": code,
        "name": "삼성전자",
        "days": days,
        "as_of": "2025-08-11",
        "color_map": {"personal": "#EF4444", "foreign": "#3B82F6", "institution": "#10B981"},
        "advisory_note": "참고용 데이터입니다. 매매 신호로 단독 사용 금지(Graham 원칙).",
        "daily": [
            {
                "date": "2025-08-11", "close": 71000,
                "personal_net": 1201, "personal_buy": 2628, "personal_sell": 1427,
                "foreign_net": -1444, "foreign_buy": 1802, "foreign_sell": 3245,
                "institution_net": -409, "institution_buy": 2933, "institution_sell": 3342,
                "institution_detail": {
                    "securities": -32, "inv_trust": -146, "private_fund": -89,
                    "bank": 2, "insurance": -61, "mrbn": -1, "pension": -83,
                    "etc_finance": 652, "etc_corp": 652, "etc_org": 0,
                },
            }
        ],
        "cumulative": [
            {"date": "2025-08-11", "personal_cum": 1201, "foreign_cum": -1444, "institution_cum": -409}
        ],
        "summary": {
            "personal_today": 1201, "foreign_today": -1444, "institution_today": -409,
            "personal_cum_total": 1201, "foreign_cum_total": -1444, "institution_cum_total": -409,
        },
    }


class TestAdvisorySupplyDemandEndpoint:

    def test_005930_default_30days(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   return_value=_fake_stock_response("005930", 30)):
            resp = client.get("/api/advisory/005930/supply-demand")
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "005930"
        assert "advisory_note" in body
        assert len(body["advisory_note"]) > 5  # 비어있지 않음

    def test_advisory_note_no_trade_signal_keys(self, client):
        """매매 액션 키 (recommendation/action/buy_signal) 부재 — OrderAdvisor 자문."""
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   return_value=_fake_stock_response("005930", 30)):
            resp = client.get("/api/advisory/005930/supply-demand?days=30")
        assert resp.status_code == 200
        body_json = resp.json()
        # 응답 dict 상위 및 daily 내부 키 검사
        for forbidden in ("recommendation", "action", "buy_signal", "trade_signal", "signal"):
            assert forbidden not in body_json, f"매매 액션 키 금지: {forbidden}"
            for d in body_json.get("daily", []):
                assert forbidden not in d, f"daily 내부 매매 액션 키 금지: {forbidden}"

    def test_non_domestic_returns_400(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   side_effect=ServiceError("국내 종목만 지원합니다.")):
            resp = client.get("/api/advisory/AAPL/supply-demand")
        assert resp.status_code == 400

    def test_not_found_returns_404(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   side_effect=NotFoundError("종목 999999 수급 데이터를 찾을 수 없습니다.")):
            resp = client.get("/api/advisory/999999/supply-demand")
        assert resp.status_code == 404

    def test_missing_kis_returns_503(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   side_effect=ConfigError("KIS API 키 설정이 필요합니다.")):
            resp = client.get("/api/advisory/005930/supply-demand")
        assert resp.status_code == 503

    def test_external_api_returns_502(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   side_effect=ExternalAPIError("KIS down")):
            resp = client.get("/api/advisory/005930/supply-demand")
        assert resp.status_code == 502

    def test_days_query_param_passed_through(self, client):
        with patch("routers.advisory.supply_demand_service.fetch_stock_supply_demand",
                   return_value=_fake_stock_response("005930", 45)) as svc:
            resp = client.get("/api/advisory/005930/supply-demand?days=45")
        assert resp.status_code == 200
        # 두 번째 인자(days)가 45로 전달되었는지
        call = svc.call_args
        days = call.kwargs.get("days") if call.kwargs else (call.args[1] if len(call.args) > 1 else None)
        assert days == 45

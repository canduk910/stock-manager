"""GET /api/macro/supply-demand 엔드포인트 테스트.

REQ-SUPPLY-ROUTER-01.
- 쿼리: market=kospi|kosdaq, days=10~60
- 200 응답 shape (daily/cumulative/summary/color_map)
- market 잘못된 값 → 422 (FastAPI Literal)
- days 범위 외 → 400 (ServiceError)
- KIS 키 미설정 → 503 (ConfigError)
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.exceptions import ConfigError, ExternalAPIError


def _fake_service_response(market="kospi", days=20):
    return {
        "market": market,
        "days": days,
        "as_of": "2024-05-17",
        "color_map": {"personal": "#EF4444", "foreign": "#3B82F6", "institution": "#10B981"},
        "daily": [
            {
                "date": "2024-05-17",
                "index_close": 2724.62,
                "personal_net": 7208,
                "foreign_net": -5975,
                "institution_net": -1507,
                "institution_detail": {
                    "securities": -189, "inv_trust": -72, "private_fund": -257,
                    "bank": 33, "insurance": -138, "mrbn": -27, "pension": -857,
                    "etc_finance": 274, "etc_corp": 274, "etc_org": 0,
                },
            }
        ],
        "cumulative": [
            {"date": "2024-05-17", "personal_cum": 7208, "foreign_cum": -5975, "institution_cum": -1507}
        ],
        "summary": {
            "personal_today": 7208, "foreign_today": -5975, "institution_today": -1507,
            "personal_cum_total": 7208, "foreign_cum_total": -5975, "institution_cum_total": -1507,
        },
    }


class TestMacroSupplyDemandEndpoint:

    def test_kospi_20days_ok(self, client):
        with patch("routers.macro.supply_demand_service.fetch_market_supply_demand",
                   return_value=_fake_service_response("kospi", 20)):
            resp = client.get("/api/macro/supply-demand?market=kospi&days=20")
        assert resp.status_code == 200
        body = resp.json()
        assert body["market"] == "kospi"
        assert body["days"] == 20
        assert "daily" in body
        assert "cumulative" in body
        assert "summary" in body
        assert "color_map" in body

    def test_kosdaq_default_days(self, client):
        with patch("routers.macro.supply_demand_service.fetch_market_supply_demand",
                   return_value=_fake_service_response("kosdaq", 20)) as svc:
            resp = client.get("/api/macro/supply-demand?market=kosdaq")
        assert resp.status_code == 200
        # 기본 20일 호출 검증
        call = svc.call_args
        # 두 번째 인자 days 또는 키워드 검사
        called_days = call.kwargs.get("days") if call.kwargs else (call.args[1] if len(call.args) > 1 else None)
        assert called_days == 20 or call.args[-1] == 20

    def test_invalid_market_returns_422(self, client):
        """FastAPI Literal 검증으로 422."""
        resp = client.get("/api/macro/supply-demand?market=fx&days=20")
        assert resp.status_code == 422

    def test_days_out_of_range_returns_400(self, client):
        """ServiceError → 400."""
        # 서비스 레이어에서 raise ServiceError (KIS 키 mock OK)
        from services.exceptions import ServiceError

        def _raise(*a, **kw):
            raise ServiceError("days는 10~60 범위여야 합니다")
        with patch("routers.macro.supply_demand_service.fetch_market_supply_demand",
                   side_effect=_raise):
            resp = client.get("/api/macro/supply-demand?market=kospi&days=100")
        assert resp.status_code == 400

    def test_missing_kis_keys_returns_503(self, client):
        with patch("routers.macro.supply_demand_service.fetch_market_supply_demand",
                   side_effect=ConfigError("KIS API 키 설정이 필요합니다.")):
            resp = client.get("/api/macro/supply-demand?market=kospi&days=20")
        assert resp.status_code == 503
        body = resp.json()
        # 상세 메시지 노출 (main.py exception_handler 패턴)
        assert "KIS" in str(body)

    def test_external_api_error_returns_502(self, client):
        with patch("routers.macro.supply_demand_service.fetch_market_supply_demand",
                   side_effect=ExternalAPIError("KIS 5xx")):
            resp = client.get("/api/macro/supply-demand?market=kospi&days=20")
        assert resp.status_code == 502

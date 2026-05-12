"""GET /api/detail/{code}/bundle 엔드포인트 테스트 (RED).

요건:
- 200 응답 + bundle shape: {basic, financials, valuation, forward_estimates, summary, partial_failure}
- market=auto (기본) 자동 판별
- 잘못된 종목코드 — 외부 API 실패 시 502 또는 부분 실패 200
"""

from __future__ import annotations

from unittest.mock import patch


class TestDetailBundleEndpoint:
    def test_bundle_endpoint_exists_and_returns_shape(self, client):
        """GET /api/detail/{code}/bundle → 200 + 키 일치."""
        with patch("services.detail_service.fetch_detail") as mock_detail, \
             patch("services.detail_service.fetch_market_metrics") as mock_metrics, \
             patch("services.detail_service.fetch_valuation_history") as mock_val_hist, \
             patch("services.detail_service.fetch_financials_multi_year") as mock_fin, \
             patch("services.detail_service.yf_client.fetch_forward_estimates_yf") as mock_fwd, \
             patch("services.detail_service.symbol_map") as mock_sym:
            mock_detail.return_value = {"close": 70000, "change": 100, "change_pct": 0.14, "mktcap": 4000000000000, "per": 10, "pbr": 1.2, "high_52": 80000, "low_52": 60000, "market_type": "KOSPI", "sector": "반도체"}
            mock_metrics.return_value = {"roe": 12.0, "dividend_yield": 2.0, "dividend_per_share": 1500, "per": 10, "pbr": 1.2}
            mock_val_hist.return_value = []
            mock_fin.return_value = [{"year": 2023, "revenue": 100, "operating_income": 10, "net_income": 8, "dart_url": ""}]
            mock_fwd.return_value = {}
            mock_sym.resolve.return_value = ("KOSPI", "삼성전자")

            resp = client.get("/api/detail/005930/bundle")
        assert resp.status_code == 200
        data = resp.json()
        for key in ("basic", "financials", "valuation", "forward_estimates", "summary"):
            assert key in data, f"응답에 {key} 키가 있어야 한다"
        assert "partial_failure" in data

    def test_bundle_with_market_query(self, client):
        """market=auto 명시도 동일 동작."""
        with patch("services.detail_service.fetch_detail") as mock_detail, \
             patch("services.detail_service.fetch_market_metrics") as mock_metrics, \
             patch("services.detail_service.fetch_valuation_history") as mock_val_hist, \
             patch("services.detail_service.fetch_financials_multi_year") as mock_fin, \
             patch("services.detail_service.yf_client.fetch_forward_estimates_yf") as mock_fwd, \
             patch("services.detail_service.symbol_map") as mock_sym:
            mock_detail.return_value = {"close": 70000, "change": 100, "change_pct": 0.14, "mktcap": None, "per": 10, "pbr": 1.2, "high_52": None, "low_52": None, "market_type": "KOSPI", "sector": "반도체"}
            mock_metrics.return_value = {"roe": None, "dividend_yield": None, "dividend_per_share": None, "per": None, "pbr": None}
            mock_val_hist.return_value = []
            mock_fin.return_value = []
            mock_fwd.return_value = {}
            mock_sym.resolve.return_value = ("KOSPI", "삼성전자")

            resp = client.get("/api/detail/005930/bundle?market=auto")
        assert resp.status_code == 200

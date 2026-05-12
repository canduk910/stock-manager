"""DetailService.get_bundle — 병렬 수집 + 부분 실패 보존 (RED).

요건:
1. detail_service.DetailService.get_bundle(code, market='auto') 가 존재한다.
2. 응답 shape: {basic, financials, valuation, forward_estimates, summary, partial_failure}
   (기존 get_report() 응답 + partial_failure)
3. 일부 섹션 실패 시: 200 status (서비스는 dict 반환) + 해당 섹션 null + partial_failure 리스트
4. 시장 자동 판별: 6자리 숫자 → KR, 알파벳 → US
"""

from __future__ import annotations

from unittest.mock import patch


class TestDetailBundleShape:
    """기본 응답 shape 검증 — 정상 케이스 (전 섹션 mock으로 합쳐서 빠르게)."""

    def test_returns_bundle_with_expected_keys(self):
        from services.detail_service import DetailService
        svc = DetailService()
        with patch.object(svc, "get_financials") as mock_fin, \
             patch.object(svc, "get_valuation_chart") as mock_val, \
             patch("services.detail_service.fetch_detail") as mock_detail, \
             patch("services.detail_service.fetch_market_metrics") as mock_metrics, \
             patch("services.detail_service.yf_client.fetch_forward_estimates_yf") as mock_fwd, \
             patch("services.detail_service.symbol_map") as mock_sym:
            mock_fin.return_value = {"code": "005930", "currency": "KRW", "rows": [{"year": 2023, "revenue": 100, "operating_profit": 10, "net_income": 8, "oi_margin": 10.0, "yoy_revenue": None, "yoy_op": None, "dart_url": ""}]}
            mock_val.return_value = {"history": [], "avg_per": None, "avg_pbr": None}
            mock_detail.return_value = {"close": 70000, "change": 100, "change_pct": 0.14, "mktcap": 4000000000000, "per": 10, "pbr": 1.2, "high_52": 80000, "low_52": 60000, "market_type": "KOSPI", "sector": "반도체"}
            mock_metrics.return_value = {"roe": 12.0, "dividend_yield": 2.0, "dividend_per_share": 1500, "per": 10, "pbr": 1.2}
            mock_fwd.return_value = {}
            mock_sym.resolve.return_value = ("KOSPI", "삼성전자")

            bundle = svc.get_bundle("005930", market="auto")

        assert isinstance(bundle, dict)
        for key in ("basic", "financials", "valuation", "forward_estimates", "summary"):
            assert key in bundle, f"bundle 응답에 {key} 키가 있어야 한다"
        assert "partial_failure" in bundle, "부분 실패 추적 키가 있어야 한다"
        assert bundle["basic"]["code"] == "005930"


class TestPartialFailure:
    """일부 섹션 실패 시 200 + null + partial_failure 보고."""

    def test_financials_failure_isolated(self):
        from services.detail_service import DetailService
        svc = DetailService()

        def _fin_fail(code, years=10):
            raise RuntimeError("DART API 오류")

        with patch.object(svc, "get_financials", side_effect=_fin_fail), \
             patch.object(svc, "get_valuation_chart") as mock_val, \
             patch("services.detail_service.fetch_detail") as mock_detail, \
             patch("services.detail_service.fetch_market_metrics") as mock_metrics, \
             patch("services.detail_service.yf_client.fetch_forward_estimates_yf") as mock_fwd, \
             patch("services.detail_service.symbol_map") as mock_sym:
            mock_val.return_value = {"history": [], "avg_per": None, "avg_pbr": None}
            mock_detail.return_value = {"close": 70000, "change": 100, "change_pct": 0.14, "mktcap": None, "per": 10, "pbr": 1.2, "high_52": None, "low_52": None, "market_type": "KOSPI", "sector": "반도체"}
            mock_metrics.return_value = {"roe": None, "dividend_yield": None, "dividend_per_share": None, "per": None, "pbr": None}
            mock_fwd.return_value = {}
            mock_sym.resolve.return_value = ("KOSPI", "삼성전자")

            bundle = svc.get_bundle("005930", market="auto")

        # 부분 실패: financials null + partial_failure에 'financials' 포함
        assert bundle["financials"] is None or bundle["financials"].get("rows") == []
        assert "financials" in bundle.get("partial_failure", [])
        # 다른 섹션은 정상 (basic은 dict)
        assert bundle["basic"] is not None
        assert isinstance(bundle["valuation"], dict)


class TestMarketAutoDetection:
    """market='auto' 시장 자동 판별 — 6자리 숫자=KR, 알파벳=US."""

    def test_us_ticker_uses_us_path(self):
        from services.detail_service import DetailService
        svc = DetailService()
        with patch.object(svc, "get_financials") as mock_fin, \
             patch.object(svc, "get_valuation_chart") as mock_val, \
             patch("services.detail_service.yf_client.fetch_detail_yf") as mock_detail_us, \
             patch("services.detail_service.yf_client.fetch_forward_estimates_yf") as mock_fwd:
            mock_fin.return_value = {"code": "AAPL", "currency": "USD", "rows": []}
            mock_val.return_value = {"history": [], "avg_per": None, "avg_pbr": None}
            mock_detail_us.return_value = {"close": 200.0, "change": 1.0, "change_pct": 0.5, "mktcap": 3000000000000, "per": 30, "pbr": 50, "roe": 150, "dividend_yield": 0.5, "dividend_per_share": 1.0, "high_52": 250, "low_52": 150, "market_type": "NASDAQ", "sector": "Technology", "name": "Apple Inc."}
            mock_fwd.return_value = {}

            bundle = svc.get_bundle("AAPL", market="auto")

        # USD currency + US 경로 사용
        assert bundle["basic"]["currency"] == "USD"
        # fetch_detail_yf 가 호출되었어야 함
        assert mock_detail_us.called

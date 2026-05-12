"""GET /api/market-board/prices 엔드포인트 테스트 (RED → GREEN).

요건:
- codes 콤마 구분, market 파라미터 (KR/US)
- 최대 50개 가드 (51개 이상 → 400)
- 응답 shape: {prices: {code: {price, change, change_pct, ...}}}
- 빈/실패 시에도 200 + 부분 결과 반환
- 예외 계층 준수 (ServiceError → HTTP)
"""

import pytest
from unittest.mock import patch


class TestMarketBoardPricesEndpoint:
    """GET /api/market-board/prices 엔드포인트."""

    def test_prices_basic_shape(self, client):
        """codes=005930,000660&market=KR → 200 + prices 키."""
        fake = {
            "005930": {"price": 72000.0, "change": 1000, "change_pct": 1.41, "prev_close": 71000.0, "volume": 100},
            "000660": {"price": 125000.0, "change": 5000, "change_pct": 4.17, "prev_close": 120000.0, "volume": 50},
        }
        with patch("routers.market_board.fetch_prices_batch", return_value=fake):
            resp = client.get("/api/market-board/prices?codes=005930,000660&market=KR")
        assert resp.status_code == 200
        data = resp.json()
        assert "prices" in data
        assert isinstance(data["prices"], dict)
        assert "005930" in data["prices"]
        assert data["prices"]["005930"]["price"] == pytest.approx(72000.0)

    def test_prices_partial_failure_returns_200(self, client):
        """외부 API 실패 시에도 200 + 부분 결과 반환."""
        with patch("routers.market_board.fetch_prices_batch", return_value={}):
            resp = client.get("/api/market-board/prices?codes=999999&market=KR")
        assert resp.status_code == 200
        data = resp.json()
        assert "prices" in data
        assert isinstance(data["prices"], dict)

    def test_prices_codes_gt_50_returns_400(self, client):
        """codes 개수가 50을 초과하면 400 에러."""
        codes = ",".join(f"{i:06d}" for i in range(51))
        resp = client.get(f"/api/market-board/prices?codes={codes}&market=KR")
        assert resp.status_code == 400

    def test_prices_empty_codes_returns_200(self, client):
        """codes 빈 문자열 → 200 + 빈 prices."""
        resp = client.get("/api/market-board/prices?codes=&market=KR")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("prices") == {}

    def test_prices_missing_codes_param_returns_422(self, client):
        """codes 파라미터 누락 → 422 (FastAPI 검증)."""
        resp = client.get("/api/market-board/prices?market=KR")
        assert resp.status_code == 422

    def test_prices_default_market_is_kr(self, client):
        """market 미지정 시 KR 디폴트."""
        with patch("routers.market_board.fetch_prices_batch", return_value={}) as mock_fn:
            resp = client.get("/api/market-board/prices?codes=005930")
        assert resp.status_code == 200
        # market 인자 검증
        call_kwargs = mock_fn.call_args.kwargs if mock_fn.call_args.kwargs else {}
        call_args = mock_fn.call_args.args if mock_fn.call_args.args else ()
        market_passed = call_kwargs.get("market") if "market" in call_kwargs else (call_args[1] if len(call_args) > 1 else None)
        assert market_passed == "KR"

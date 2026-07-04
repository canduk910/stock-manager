"""F-4 (2026-07-04): 관심종목 KR 현재가 fetch_prices_batch 프리페치 회귀 가드.

value-screener CAUTION 제약 검증:
- 배치 응답 shape 매핑 (price 키 → close, mktcap 부재)
- 시총은 metrics(6h 캐시) 소싱 — 배치 전환으로 인한 시총 결측 방지
- 배치 누락 종목은 per-code fetch_price 폴백 (결측이 조용히 삼켜지지 않음)
- 2건 미만은 배치 미사용
"""
from unittest.mock import patch

import services.watchlist_service as ws
from services.watchlist_service import WatchlistService, _prefetch_kr_prices


_BATCH_RAW = {
    "005930": {"price": 71000, "change": 500, "change_pct": 0.7, "prev_close": 70500,
               "volume": 1000, "sign": "2"},
    "000660": {"price": 210000, "change": -1000, "change_pct": -0.5, "prev_close": 211000,
               "volume": 500, "sign": "5"},
}


def _fake_metrics(code):
    return {"market_type": "KOSPI", "mktcap": 400_0000_0000, "per": 10, "pbr": 1.0,
            "roe": 8, "dividend_yield": 2, "sector": "반도체"}


class TestPrefetchHelper:
    def test_normalizes_batch_keys_to_fetch_price_shape(self):
        """배치 price 키 → close 정규화. mktcap은 의도적으로 미포함."""
        with patch.object(ws, "fetch_prices_batch", return_value=_BATCH_RAW):
            out = _prefetch_kr_prices(["005930", "000660"])
        assert out["005930"]["close"] == 71000
        assert out["005930"]["change_pct"] == 0.7
        assert "mktcap" not in out["005930"]

    def test_single_code_skips_batch(self):
        """2건 미만이면 배치 호출 없이 빈 dict (per-code 경로 유지)."""
        with patch.object(ws, "fetch_prices_batch") as mock_batch:
            assert _prefetch_kr_prices(["005930"]) == {}
        mock_batch.assert_not_called()

    def test_batch_failure_returns_empty(self):
        """배치 예외 → 빈 dict — 호출측 per-code 폴백으로 결측 방지."""
        with patch.object(ws, "fetch_prices_batch", side_effect=RuntimeError("yf down")):
            assert _prefetch_kr_prices(["005930", "000660"]) == {}


class TestBatchDetailsPrefetch:
    def test_prefetch_hit_skips_per_code_fetch_price(self, db_session):
        """배치 hit 종목은 fetch_price 미호출 + 시총은 metrics 소싱."""
        svc = WatchlistService()
        with patch.object(ws, "fetch_prices_batch", return_value=_BATCH_RAW), \
             patch.object(ws, "fetch_market_metrics", side_effect=_fake_metrics), \
             patch.object(ws, "fetch_price") as mock_fp:
            result = svc.fetch_batch_details(["005930", "000660"], market="KR")
        mock_fp.assert_not_called()
        d = result["details"]["005930"]
        assert d["price"] == 71000
        assert d["change_pct"] == 0.7
        # 배치에 mktcap 없음 → metrics.mktcap(400억원 → _awk 억원 단위) 소싱
        assert d["market_cap"] == 400
        assert result["errors"] == []

    def test_prefetch_miss_falls_back_to_fetch_price(self, db_session):
        """배치 응답 누락 종목 → per-code fetch_price 폴백 (기존 시맨틱)."""
        only_one = {"005930": _BATCH_RAW["005930"]}
        svc = WatchlistService()
        with patch.object(ws, "fetch_prices_batch", return_value=only_one), \
             patch.object(ws, "fetch_market_metrics", side_effect=_fake_metrics), \
             patch.object(ws, "fetch_price",
                          return_value={"close": 209000, "change": 0, "change_pct": 0,
                                        "mktcap": 100_0000_0000}) as mock_fp:
            result = svc.fetch_batch_details(["005930", "000660"], market="KR")
        mock_fp.assert_called_once_with("000660")
        assert result["details"]["000660"]["price"] == 209000


class TestDashboardPrefetch:
    def test_dashboard_rows_use_prefetched_price(self, db_session):
        """대시보드 2종목: 배치 1회 + 행별 주입, fetch_price 미호출."""
        items = [
            {"code": "005930", "name": "삼성전자", "market": "KR"},
            {"code": "000660", "name": "SK하이닉스", "market": "KR"},
        ]
        svc = WatchlistService()
        with patch.object(ws, "fetch_prices_batch", return_value=_BATCH_RAW) as mock_batch, \
             patch.object(ws, "fetch_market_metrics", side_effect=_fake_metrics), \
             patch.object(ws, "fetch_price") as mock_fp, \
             patch("stock.stock_info_store.get_stock_info", return_value=None), \
             patch("services.watchlist_service.fetch_financials", return_value=None):
            rows = svc.get_dashboard_data(items)
        assert mock_batch.call_count == 1
        mock_fp.assert_not_called()
        by_code = {r["code"]: r for r in rows}
        assert by_code["005930"]["price"] == 71000
        assert "price" not in by_code["005930"]["partial_failure"]
        # 배치에 mktcap 없음 → metrics(stale 경로) 소싱: 400억
        assert by_code["005930"]["market_cap"] == 400

    def test_dashboard_prefetch_miss_falls_back(self, db_session):
        """배치 누락 행은 per-code fetch_price 폴백."""
        items = [
            {"code": "005930", "name": "삼성전자", "market": "KR"},
            {"code": "000660", "name": "SK하이닉스", "market": "KR"},
        ]
        only_one = {"005930": _BATCH_RAW["005930"]}
        svc = WatchlistService()
        with patch.object(ws, "fetch_prices_batch", return_value=only_one), \
             patch.object(ws, "fetch_market_metrics", side_effect=_fake_metrics), \
             patch.object(ws, "fetch_price",
                          return_value={"close": 209000, "change": 0, "change_pct": 0,
                                        "mktcap": 100_0000_0000}) as mock_fp, \
             patch("stock.stock_info_store.get_stock_info", return_value=None), \
             patch("services.watchlist_service.fetch_financials", return_value=None):
            rows = svc.get_dashboard_data(items)
        mock_fp.assert_called_once_with("000660")
        by_code = {r["code"]: r for r in rows}
        assert by_code["000660"]["price"] == 209000

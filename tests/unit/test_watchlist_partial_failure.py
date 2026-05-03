"""QW-3: _fetch_dashboard_row partial_failure 메타필드 + logger.warning 검증.

- 정상 케이스: partial_failure == [] (또는 부재)
- price 실패: partial_failure == ["price"]
- 모든 영역 실패: row 자체 반환 + partial_failure 모든 영역
- 외부 API 실패는 logger.warning으로 기록 (기존 logger.debug → logger.warning 승격)
"""

import logging
from unittest.mock import patch

import pytest


@pytest.fixture
def kr_item():
    return {"code": "005930", "name": "삼성전자", "memo": "", "market": "KR"}


class TestPartialFailure:
    """partial_failure 메타필드 검증."""

    def test_success_no_partial_failure(self, kr_item):
        from services import watchlist_service as ws

        with patch.object(ws, "fetch_price", return_value={
                "close": 70000, "change": 100, "change_pct": 0.14, "mktcap": 4_000_000_000_000_000}), \
             patch.object(ws, "fetch_market_metrics", return_value={"dividend_yield": 2.0, "sector": "반도체"}), \
             patch.object(ws, "fetch_financials", return_value={
                "bsns_year": "2024", "revenue": 1_000_000, "operating_income": 100_000, "net_income": 80_000}), \
             patch("stock.stock_info_store.get_stock_info", return_value=None):
            row = ws._fetch_dashboard_row(kr_item)

        assert row["price"] == 70000
        # partial_failure는 빈 리스트이거나 부재
        assert row.get("partial_failure", []) == []

    def test_price_failure_records_partial(self, kr_item, caplog):
        from services import watchlist_service as ws

        with patch.object(ws, "fetch_price", side_effect=RuntimeError("kis down")), \
             patch.object(ws, "fetch_market_metrics", return_value={"dividend_yield": 2.0, "sector": "반도체"}), \
             patch.object(ws, "fetch_financials", return_value={
                "bsns_year": "2024", "revenue": 1_000_000, "operating_income": 100_000, "net_income": 80_000}), \
             patch("stock.stock_info_store.get_stock_info", return_value=None), \
             caplog.at_level(logging.WARNING, logger=ws.logger.name):
            row = ws._fetch_dashboard_row(kr_item)

        assert row["price"] is None
        assert "price" in row.get("partial_failure", [])
        # 경고 로그 발생
        assert any("price" in rec.message.lower() or rec.levelno == logging.WARNING
                   for rec in caplog.records)

    def test_all_failure_returns_row(self, kr_item):
        from services import watchlist_service as ws

        with patch.object(ws, "fetch_price", side_effect=RuntimeError("p")), \
             patch.object(ws, "fetch_market_metrics", side_effect=RuntimeError("m")), \
             patch.object(ws, "fetch_financials", side_effect=RuntimeError("f")), \
             patch("stock.stock_info_store.get_stock_info", return_value=None):
            row = ws._fetch_dashboard_row(kr_item)

        # row 자체는 반환된다 (None 아님)
        assert row is not None
        assert row["code"] == "005930"
        pf = row.get("partial_failure", [])
        assert "price" in pf
        assert "metrics" in pf
        assert "financials" in pf

    def test_overseas_partial_failure(self):
        from services import watchlist_service as ws
        item = {"code": "AAPL", "name": "Apple", "memo": "", "market": "US"}

        with patch("stock.yf_client.fetch_price_yf", side_effect=RuntimeError("yf")), \
             patch("stock.yf_client.fetch_detail_yf", return_value={"dividend_yield": 0.5, "sector": "Tech"}), \
             patch("stock.yf_client.fetch_financials_yf", return_value=None), \
             patch("stock.stock_info_store.get_stock_info", return_value=None):
            row = ws._fetch_dashboard_row(item)

        assert row["code"] == "AAPL"
        pf = row.get("partial_failure", [])
        assert "price" in pf


# ── QW-1: dict 기반 stock_info 단축회로 검증 ──────────────────────────────

class TestStockInfoDictShortcut:
    """fresh stock_info 있으면 외부 API 미호출 + DB SELECT 1회만."""

    def test_all_fresh_skips_external_api(self, kr_item):
        from services import watchlist_service as ws
        from datetime import datetime, timedelta
        from db.utils import KST

        now = datetime.now(KST).replace(tzinfo=None)
        recent = (now - timedelta(minutes=5)).isoformat(timespec="seconds")
        old_recent = (now - timedelta(hours=1)).isoformat(timespec="seconds")
        info = {
            "code": "005930", "market": "KR",
            "price": 70000, "change_val": 100, "change_pct": 0.14,
            "mktcap": 4_000_000_000_000_000,
            "dividend_yield": 2.0, "sector": "반도체",
            "revenue": 1_000_000, "operating_income": 100_000, "net_income": 80_000,
            "bsns_year": "2024",
            "price_updated_at": recent,
            "metrics_updated_at": recent,
            "fin_updated_at": old_recent,
        }

        price_mock = patch.object(ws, "fetch_price", side_effect=AssertionError("should not be called"))
        with patch("stock.stock_info_store.get_stock_info", return_value=info), \
             price_mock:
            row = ws._fetch_dashboard_row(kr_item)

        # 모든 영역 fresh → 외부 API 호출 없이 stock_info에서 채워짐
        assert row["price"] == 70000
        assert row["dividend_yield"] == 2.0
        assert row["revenue"] is not None

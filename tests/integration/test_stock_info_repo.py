"""StockInfoRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.stock_info_repo import StockInfoRepository


class TestStockInfoGet:
    def test_get_stock_info_empty(self, db_session):
        repo = StockInfoRepository(db_session)
        result = repo.get_stock_info("005930", "KR")
        assert result is None

    def test_upsert_and_get(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_price("005930", "KR", {
            "close": 62000, "change_val": 500, "change_pct": 0.81,
            "mktcap": 370_000_000_000_000, "shares": 5_969_782_550,
        })
        db_session.commit()

        info = repo.get_stock_info("005930", "KR")
        assert info is not None
        assert info["price"] == 62000
        assert info["change_val"] == 500
        assert info["price_updated_at"] is not None

    def test_upsert_metrics(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_metrics("005930", "KR", {
            "per": 12.5, "pbr": 1.2, "roe": 15.0,
            "dividend_yield": 2.5, "market_type": "KOSPI",
        })
        db_session.commit()

        info = repo.get_stock_info("005930", "KR")
        assert info["per"] == 12.5
        assert info["roe"] == 15.0
        assert info["metrics_updated_at"] is not None

    def test_upsert_financials(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_financials("005930", "KR", {
            "revenue": 300_000_000, "operating_income": 50_000_000,
            "net_income": 40_000_000, "bsns_year": 2025,
        })
        db_session.commit()

        info = repo.get_stock_info("005930", "KR")
        assert info["revenue"] == 300_000_000
        assert info["bsns_year"] == 2025

    def test_upsert_returns(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_returns("005930", "KR", {
            "return_3m": 5.5, "return_6m": 10.2, "return_1y": 15.8,
        })
        db_session.commit()

        info = repo.get_stock_info("005930", "KR")
        assert info["return_3m"] == 5.5
        assert info["return_1y"] == 15.8

    def test_upsert_overwrites(self, db_session):
        """같은 종목에 두번 upsert하면 덮어쓰기."""
        repo = StockInfoRepository(db_session)
        repo.upsert_price("005930", "KR", {"close": 60000})
        db_session.commit()

        repo.upsert_price("005930", "KR", {"close": 65000})
        db_session.commit()

        info = repo.get_stock_info("005930", "KR")
        assert info["price"] == 65000


class TestStockInfoBatchGet:
    def test_batch_get(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_price("005930", "KR", {"close": 62000})
        repo.upsert_price("AAPL", "US", {"close": 150})
        db_session.commit()

        result = repo.batch_get([("005930", "KR"), ("AAPL", "US")])
        assert len(result) == 2
        assert ("005930", "KR") in result
        assert ("AAPL", "US") in result
        assert result[("005930", "KR")]["price"] == 62000

    def test_batch_get_empty(self, db_session):
        repo = StockInfoRepository(db_session)
        result = repo.batch_get([])
        assert result == {}

    def test_batch_get_partial(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_price("005930", "KR", {"close": 62000})
        db_session.commit()

        result = repo.batch_get([("005930", "KR"), ("NOEXIST", "KR")])
        assert len(result) == 1


class TestStockInfoStale:
    def test_is_stale_no_data(self, db_session):
        repo = StockInfoRepository(db_session)
        assert repo.is_stale("005930", "KR", "price") is True

    def test_is_stale_fresh(self, db_session):
        repo = StockInfoRepository(db_session)
        repo.upsert_price("005930", "KR", {"close": 62000})
        db_session.commit()

        # 방금 저장한 데이터는 fresh
        assert repo.is_stale("005930", "KR", "price") is False

    def test_is_stale_no_field(self, db_session):
        """metrics만 저장했는데 price staleness 확인."""
        repo = StockInfoRepository(db_session)
        repo.upsert_metrics("005930", "KR", {"per": 12.5})
        db_session.commit()

        # price_updated_at은 None이므로 stale
        assert repo.is_stale("005930", "KR", "price") is True

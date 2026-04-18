"""WatchlistRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.watchlist_repo import WatchlistRepository


class TestWatchlistAdd:
    def test_add_and_get(self, db_session):
        repo = WatchlistRepository(db_session)
        ok = repo.add_item("005930", "삼성전자", memo="반도체 대장", market="KR")
        db_session.commit()
        assert ok is True

        item = repo.get_item("005930", "KR")
        assert item is not None
        assert item["name"] == "삼성전자"
        assert item["code"] == "005930"
        assert item["memo"] == "반도체 대장"

    def test_add_duplicate(self, db_session):
        repo = WatchlistRepository(db_session)
        repo.add_item("005930", "삼성전자", market="KR")
        db_session.commit()

        ok = repo.add_item("005930", "삼성전자", market="KR")
        assert ok is False

    def test_add_same_code_different_market(self, db_session):
        repo = WatchlistRepository(db_session)
        ok1 = repo.add_item("005930", "삼성전자", market="KR")
        ok2 = repo.add_item("005930", "Samsung", market="US")
        db_session.commit()
        assert ok1 is True
        assert ok2 is True


class TestWatchlistRemove:
    def test_remove(self, db_session):
        repo = WatchlistRepository(db_session)
        repo.add_item("005930", "삼성전자")
        db_session.commit()

        ok = repo.remove_item("005930")
        db_session.commit()
        assert ok is True

        item = repo.get_item("005930")
        assert item is None

    def test_remove_nonexistent(self, db_session):
        repo = WatchlistRepository(db_session)
        ok = repo.remove_item("999999")
        assert ok is False


class TestWatchlistUpdateMemo:
    def test_update_memo(self, db_session):
        repo = WatchlistRepository(db_session)
        repo.add_item("005930", "삼성전자", memo="old")
        db_session.commit()

        ok = repo.update_memo("005930", "new memo")
        db_session.commit()
        assert ok is True

        item = repo.get_item("005930")
        assert item["memo"] == "new memo"

    def test_update_memo_nonexistent(self, db_session):
        repo = WatchlistRepository(db_session)
        ok = repo.update_memo("999999", "test")
        assert ok is False


class TestWatchlistAllItems:
    def test_all_items(self, db_session):
        repo = WatchlistRepository(db_session)
        repo.add_item("005930", "삼성전자")
        repo.add_item("000660", "SK하이닉스")
        db_session.commit()

        items = repo.all_items()
        assert len(items) == 2
        codes = [it["code"] for it in items]
        assert "005930" in codes
        assert "000660" in codes

    def test_all_items_empty(self, db_session):
        repo = WatchlistRepository(db_session)
        items = repo.all_items()
        assert items == []


class TestWatchlistMarketFilter:
    def test_market_filter(self, db_session):
        repo = WatchlistRepository(db_session)
        repo.add_item("005930", "삼성전자", market="KR")
        repo.add_item("AAPL", "Apple", market="US")
        db_session.commit()

        kr = repo.get_item("005930", "KR")
        assert kr is not None
        assert kr["market"] == "KR"

        us = repo.get_item("AAPL", "US")
        assert us is not None
        assert us["market"] == "US"

        # 다른 마켓으로 조회하면 None
        assert repo.get_item("005930", "US") is None


class TestWatchlistOrder:
    def test_save_and_get_order(self, db_session):
        repo = WatchlistRepository(db_session)
        order_items = [
            {"code": "005930", "market": "KR"},
            {"code": "000660", "market": "KR"},
            {"code": "AAPL", "market": "US"},
        ]
        repo.save_order(order_items)
        db_session.commit()

        order = repo.get_order()
        assert len(order) == 3
        assert order[0]["code"] == "005930"
        assert order[0]["position"] == 0
        assert order[1]["code"] == "000660"
        assert order[1]["position"] == 1
        assert order[2]["code"] == "AAPL"
        assert order[2]["position"] == 2

    def test_save_order_replaces(self, db_session):
        repo = WatchlistRepository(db_session)
        repo.save_order([{"code": "005930", "market": "KR"}])
        db_session.commit()

        # 새로운 순서로 교체
        repo.save_order([
            {"code": "AAPL", "market": "US"},
            {"code": "005930", "market": "KR"},
        ])
        db_session.commit()

        order = repo.get_order()
        assert len(order) == 2
        assert order[0]["code"] == "AAPL"
        assert order[1]["code"] == "005930"

    def test_get_order_empty(self, db_session):
        repo = WatchlistRepository(db_session)
        order = repo.get_order()
        assert order == []

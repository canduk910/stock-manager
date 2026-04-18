"""MarketBoardRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.market_board_repo import MarketBoardRepository


class TestMarketBoardAdd:
    def test_add_item(self, db_session):
        repo = MarketBoardRepository(db_session)
        ok = repo.add_item("005930", "삼성전자", market="KR")
        db_session.commit()
        assert ok is True

        items = repo.all_items()
        assert len(items) == 1
        assert items[0]["code"] == "005930"
        assert items[0]["name"] == "삼성전자"

    def test_add_duplicate(self, db_session):
        repo = MarketBoardRepository(db_session)
        repo.add_item("005930", "삼성전자")
        db_session.commit()

        ok = repo.add_item("005930", "삼성전자")
        assert ok is False


class TestMarketBoardRemove:
    def test_remove_item(self, db_session):
        repo = MarketBoardRepository(db_session)
        repo.add_item("005930", "삼성전자")
        db_session.commit()

        ok = repo.remove_item("005930")
        db_session.commit()
        assert ok is True

        items = repo.all_items()
        assert len(items) == 0

    def test_remove_nonexistent(self, db_session):
        repo = MarketBoardRepository(db_session)
        ok = repo.remove_item("999999")
        assert ok is False


class TestMarketBoardAllItems:
    def test_all_items(self, db_session):
        repo = MarketBoardRepository(db_session)
        repo.add_item("005930", "삼성전자")
        repo.add_item("000660", "SK하이닉스")
        db_session.commit()

        items = repo.all_items()
        assert len(items) == 2

    def test_all_items_empty(self, db_session):
        repo = MarketBoardRepository(db_session)
        assert repo.all_items() == []


class TestMarketBoardOrder:
    def test_save_and_get_order(self, db_session):
        repo = MarketBoardRepository(db_session)
        order_items = [
            {"code": "005930", "market": "KR"},
            {"code": "AAPL", "market": "US"},
        ]
        repo.save_order(order_items)
        db_session.commit()

        order = repo.get_order()
        assert len(order) == 2
        assert order[0]["code"] == "005930"
        assert order[0]["position"] == 0
        assert order[1]["code"] == "AAPL"
        assert order[1]["position"] == 1

    def test_save_order_replaces(self, db_session):
        repo = MarketBoardRepository(db_session)
        repo.save_order([{"code": "005930", "market": "KR"}])
        db_session.commit()

        repo.save_order([
            {"code": "AAPL", "market": "US"},
            {"code": "005930", "market": "KR"},
        ])
        db_session.commit()

        order = repo.get_order()
        assert len(order) == 2
        assert order[0]["code"] == "AAPL"

    def test_get_order_empty(self, db_session):
        repo = MarketBoardRepository(db_session)
        assert repo.get_order() == []

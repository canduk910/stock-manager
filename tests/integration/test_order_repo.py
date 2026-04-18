"""OrderRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.order_repo import OrderRepository


class TestInsertOrder:
    def test_insert_order(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
        )
        db_session.commit()

        assert order["id"] > 0
        assert order["symbol"] == "005930"
        assert order["side"] == "buy"
        assert order["status"] == "PLACED"
        assert order["placed_at"] is not None

    def test_insert_order_pending(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
            status="PENDING",
        )
        db_session.commit()
        assert order["status"] == "PENDING"

    def test_insert_order_with_order_no(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
            order_no="ORD001", org_no="ORG001",
        )
        db_session.commit()
        assert order["order_no"] == "ORD001"
        assert order["org_no"] == "ORG001"


class TestUpdateOrderStatus:
    def test_update_status_filled(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
        )
        db_session.commit()

        updated = repo.update_order_status(
            order["id"], "FILLED",
            filled_quantity=10, filled_price=62000,
        )
        db_session.commit()

        assert updated["status"] == "FILLED"
        assert updated["filled_at"] is not None
        assert updated["filled_quantity"] == 10
        assert updated["filled_price"] == 62000

    def test_update_status_cancelled(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
        )
        db_session.commit()

        updated = repo.update_order_status(order["id"], "CANCELLED")
        db_session.commit()
        assert updated["status"] == "CANCELLED"
        assert updated["filled_at"] is None

    def test_update_nonexistent(self, db_session):
        repo = OrderRepository(db_session)
        result = repo.update_order_status(99999, "FILLED")
        assert result is None


class TestGetOrder:
    def test_get_order_by_id(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
        )
        db_session.commit()

        fetched = repo.get_order(order["id"])
        assert fetched is not None
        assert fetched["id"] == order["id"]
        assert fetched["symbol"] == "005930"

    def test_get_order_nonexistent(self, db_session):
        repo = OrderRepository(db_session)
        assert repo.get_order(99999) is None

    def test_get_order_by_order_no(self, db_session):
        repo = OrderRepository(db_session)
        repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
            order_no="ORD001",
        )
        db_session.commit()

        fetched = repo.get_order_by_order_no("ORD001", "KR")
        assert fetched is not None
        assert fetched["order_no"] == "ORD001"

    def test_get_order_by_order_no_returns_latest(self, db_session):
        repo = OrderRepository(db_session)
        repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=60000, quantity=10,
            order_no="ORD001",
        )
        repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
            order_no="ORD001",
        )
        db_session.commit()

        fetched = repo.get_order_by_order_no("ORD001", "KR")
        assert fetched["price"] == 62000  # 최신 것


class TestListOrders:
    def test_list_orders_filter(self, db_session):
        repo = OrderRepository(db_session)
        repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
        )
        repo.insert_order(
            symbol="AAPL", symbol_name="Apple", market="US",
            side="sell", order_type="market", price=150, quantity=5,
        )
        db_session.commit()

        kr_orders = repo.list_orders(market="KR")
        assert len(kr_orders) == 1
        assert kr_orders[0]["symbol"] == "005930"

        buy_orders = repo.list_orders(symbol="AAPL")
        assert len(buy_orders) == 1

    def test_list_active_orders(self, db_session):
        repo = OrderRepository(db_session)
        o1 = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
            status="PLACED",
        )
        o2 = repo.insert_order(
            symbol="000660", symbol_name="SK하이닉스", market="KR",
            side="buy", order_type="limit", price=100000, quantity=5,
            status="PENDING",
        )
        o3 = repo.insert_order(
            symbol="AAPL", symbol_name="Apple", market="US",
            side="sell", order_type="market", price=150, quantity=5,
        )
        db_session.commit()

        # o3을 FILLED로 변경
        repo.update_order_status(o3["id"], "FILLED")
        db_session.commit()

        active = repo.list_active_orders()
        assert len(active) == 2
        statuses = {o["status"] for o in active}
        assert statuses == {"PLACED", "PENDING"}


class TestUpdateOrderDetails:
    def test_update_order_details(self, db_session):
        repo = OrderRepository(db_session)
        order = repo.insert_order(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=62000, quantity=10,
        )
        db_session.commit()

        updated = repo.update_order_details(
            order["id"], price=63000, quantity=20,
        )
        db_session.commit()
        assert updated["price"] == 63000
        assert updated["quantity"] == 20

    def test_update_order_details_nonexistent(self, db_session):
        repo = OrderRepository(db_session)
        result = repo.update_order_details(99999, price=63000)
        assert result is None


class TestReservation:
    def test_insert_reservation(self, db_session):
        repo = OrderRepository(db_session)
        res = repo.insert_reservation(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=60000, quantity=10,
            condition_type="price_below", condition_value="61000",
        )
        db_session.commit()

        assert res["id"] > 0
        assert res["condition_type"] == "price_below"
        assert res["status"] == "WAITING"

    def test_list_reservations(self, db_session):
        repo = OrderRepository(db_session)
        repo.insert_reservation(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=60000, quantity=10,
            condition_type="price_below", condition_value="61000",
        )
        repo.insert_reservation(
            symbol="AAPL", symbol_name="Apple", market="US",
            side="buy", order_type="limit", price=140, quantity=5,
            condition_type="time", condition_value="09:00",
        )
        db_session.commit()

        all_res = repo.list_reservations()
        assert len(all_res) == 2

        waiting = repo.list_reservations(status="WAITING")
        assert len(waiting) == 2

    def test_update_reservation_status(self, db_session):
        repo = OrderRepository(db_session)
        res = repo.insert_reservation(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=60000, quantity=10,
            condition_type="price_below", condition_value="61000",
        )
        db_session.commit()

        updated = repo.update_reservation_status(
            res["id"], "TRIGGERED", result_order_no="ORD001",
        )
        db_session.commit()

        assert updated["status"] == "TRIGGERED"
        assert updated["triggered_at"] is not None
        assert updated["result_order_no"] == "ORD001"

    def test_delete_reservation(self, db_session):
        repo = OrderRepository(db_session)
        res = repo.insert_reservation(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=60000, quantity=10,
            condition_type="price_below", condition_value="61000",
        )
        db_session.commit()

        ok = repo.delete_reservation(res["id"])
        db_session.commit()
        assert ok is True

        # 삭제 후 조회
        assert repo.get_reservation(res["id"]) is None

    def test_delete_reservation_not_waiting(self, db_session):
        """WAITING이 아닌 예약은 삭제 불가."""
        repo = OrderRepository(db_session)
        res = repo.insert_reservation(
            symbol="005930", symbol_name="삼성전자", market="KR",
            side="buy", order_type="limit", price=60000, quantity=10,
            condition_type="price_below", condition_value="61000",
        )
        db_session.commit()

        repo.update_reservation_status(res["id"], "TRIGGERED")
        db_session.commit()

        ok = repo.delete_reservation(res["id"])
        assert ok is False

    def test_delete_reservation_nonexistent(self, db_session):
        repo = OrderRepository(db_session)
        ok = repo.delete_reservation(99999)
        assert ok is False

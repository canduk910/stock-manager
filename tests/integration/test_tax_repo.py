"""TaxRepository 통합 테스트 — 인메모리 SQLite."""

import pytest
from db.repositories.tax_repo import TaxRepository


class TestTaxTransaction:
    def test_insert_transaction(self, db_session):
        repo = TaxRepository(db_session)
        tx = repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
            symbol_name="Apple", currency="USD", exchange_rate=1300.0,
            price_krw=195000.0,
        )
        db_session.commit()

        assert tx["id"] > 0
        assert tx["symbol"] == "AAPL"
        assert tx["side"] == "buy"
        assert tx["quantity"] == 100
        assert tx["price_foreign"] == 150.0
        assert tx["currency"] == "USD"

    def test_list_transactions_by_year(self, db_session):
        repo = TaxRepository(db_session)
        repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2025-06-15",
        )
        repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="sell",
            quantity=50, price_foreign=180.0, trade_date="2026-03-20",
        )
        db_session.commit()

        tx_2025 = repo.list_transactions(year=2025)
        assert len(tx_2025) == 1
        assert tx_2025[0]["trade_date"] == "2025-06-15"

        tx_2026 = repo.list_transactions(year=2026)
        assert len(tx_2026) == 1

    def test_list_transactions_by_symbol(self, db_session):
        repo = TaxRepository(db_session)
        repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
        )
        repo.insert_transaction(
            source="MANUAL", symbol="MSFT", side="buy",
            quantity=50, price_foreign=300.0, trade_date="2026-01-15",
        )
        db_session.commit()

        aapl_tx = repo.list_transactions(symbol="AAPL")
        assert len(aapl_tx) == 1
        assert aapl_tx[0]["symbol"] == "AAPL"

    def test_list_transactions_by_side(self, db_session):
        repo = TaxRepository(db_session)
        repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
        )
        repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="sell",
            quantity=50, price_foreign=180.0, trade_date="2026-02-15",
        )
        db_session.commit()

        buy_tx = repo.list_transactions(side="buy")
        assert len(buy_tx) == 1

        sell_tx = repo.list_transactions(side="sell")
        assert len(sell_tx) == 1

    def test_get_transaction(self, db_session):
        repo = TaxRepository(db_session)
        tx = repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
        )
        db_session.commit()

        fetched = repo.get_transaction(tx["id"])
        assert fetched is not None
        assert fetched["id"] == tx["id"]

    def test_get_transaction_nonexistent(self, db_session):
        repo = TaxRepository(db_session)
        assert repo.get_transaction(99999) is None

    def test_delete_transaction(self, db_session):
        repo = TaxRepository(db_session)
        tx = repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
        )
        db_session.commit()

        ok = repo.delete_transaction(tx["id"])
        db_session.commit()
        assert ok is True

        assert repo.get_transaction(tx["id"]) is None

    def test_delete_transaction_nonexistent(self, db_session):
        repo = TaxRepository(db_session)
        ok = repo.delete_transaction(99999)
        assert ok is False

    def test_exists_by_key(self, db_session):
        repo = TaxRepository(db_session)
        repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
        )
        db_session.commit()

        assert repo.exists_by_key("AAPL", "buy", "2026-01-15", 150.0, 100) is True
        assert repo.exists_by_key("AAPL", "buy", "2026-01-15", 151.0, 100) is False
        assert repo.exists_by_key("MSFT", "buy", "2026-01-15", 150.0, 100) is False

    def test_get_by_source_order_id(self, db_session):
        repo = TaxRepository(db_session)
        repo.insert_transaction(
            source="KIS", symbol="AAPL", side="buy",
            quantity=100, price_foreign=150.0, trade_date="2026-01-15",
            source_order_id=42,
        )
        db_session.commit()

        found = repo.get_by_source_order_id(42)
        assert found is not None
        assert found["source_order_id"] == 42

        assert repo.get_by_source_order_id(999) is None


class TestTaxCalculation:
    def _insert_sell_tx(self, repo, db_session):
        tx = repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="sell",
            quantity=50, price_foreign=180.0, trade_date="2026-03-20",
        )
        db_session.commit()
        return tx

    def test_insert_calculation(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx = self._insert_sell_tx(repo, db_session)

        calc = repo.insert_calculation(
            sell_tx_id=sell_tx["id"],
            symbol="AAPL",
            method="FIFO",
            sell_quantity=50,
            sell_price_krw=11_700_000,
            acquisition_cost_krw=9_750_000,
            commission_total_krw=5000,
            gain_loss_krw=1_945_000,
            trade_date="2026-03-20",
            year=2026,
        )
        db_session.commit()

        assert calc["id"] > 0
        assert calc["method"] == "FIFO"
        assert calc["gain_loss_krw"] == 1_945_000

    def test_list_calculations(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx = self._insert_sell_tx(repo, db_session)

        repo.insert_calculation(
            sell_tx_id=sell_tx["id"], symbol="AAPL", method="FIFO",
            sell_quantity=50, sell_price_krw=11_700_000,
            acquisition_cost_krw=9_750_000, commission_total_krw=5000,
            gain_loss_krw=1_945_000, trade_date="2026-03-20", year=2026,
        )
        db_session.commit()

        calcs = repo.list_calculations(year=2026)
        assert len(calcs) == 1
        assert calcs[0]["symbol"] == "AAPL"

        calcs_2025 = repo.list_calculations(year=2025)
        assert len(calcs_2025) == 0

    def test_list_calculations_by_symbol(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx = self._insert_sell_tx(repo, db_session)

        repo.insert_calculation(
            sell_tx_id=sell_tx["id"], symbol="AAPL", method="FIFO",
            sell_quantity=50, sell_price_krw=11_700_000,
            acquisition_cost_krw=9_750_000, commission_total_krw=0,
            gain_loss_krw=1_950_000, trade_date="2026-03-20", year=2026,
        )
        db_session.commit()

        calcs = repo.list_calculations(year=2026, symbol="AAPL")
        assert len(calcs) == 1

        calcs = repo.list_calculations(year=2026, symbol="MSFT")
        assert len(calcs) == 0

    def test_delete_calculations_by_year(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx = self._insert_sell_tx(repo, db_session)

        repo.insert_calculation(
            sell_tx_id=sell_tx["id"], symbol="AAPL", method="FIFO",
            sell_quantity=50, sell_price_krw=11_700_000,
            acquisition_cost_krw=9_750_000, commission_total_krw=0,
            gain_loss_krw=1_950_000, trade_date="2026-03-20", year=2026,
        )
        db_session.commit()

        deleted = repo.delete_calculations_by_year(2026, "FIFO")
        db_session.commit()
        assert deleted == 1

        assert repo.list_calculations(year=2026) == []


class TestTaxFifoLot:
    def _setup_calc(self, repo, db_session):
        sell_tx = repo.insert_transaction(
            source="MANUAL", symbol="AAPL", side="sell",
            quantity=50, price_foreign=180.0, trade_date="2026-03-20",
        )
        db_session.commit()
        calc = repo.insert_calculation(
            sell_tx_id=sell_tx["id"], symbol="AAPL", method="FIFO",
            sell_quantity=50, sell_price_krw=11_700_000,
            acquisition_cost_krw=9_750_000, commission_total_krw=0,
            gain_loss_krw=1_950_000, trade_date="2026-03-20", year=2026,
        )
        db_session.commit()
        return sell_tx, calc

    def test_insert_fifo_lot(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx, calc = self._setup_calc(repo, db_session)

        lot = repo.insert_fifo_lot(
            calculation_id=calc["id"],
            sell_tx_id=sell_tx["id"],
            symbol="AAPL",
            quantity=50,
            buy_tx_id=1,
            buy_price_krw=195000.0,
            buy_trade_date="2026-01-15",
            cost_krw=9_750_000.0,
        )
        db_session.commit()

        assert lot["id"] > 0
        assert lot["quantity"] == 50
        assert lot["symbol"] == "AAPL"

    def test_list_fifo_lots(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx, calc = self._setup_calc(repo, db_session)

        repo.insert_fifo_lot(
            calculation_id=calc["id"], sell_tx_id=sell_tx["id"],
            symbol="AAPL", quantity=30, buy_tx_id=1,
        )
        repo.insert_fifo_lot(
            calculation_id=calc["id"], sell_tx_id=sell_tx["id"],
            symbol="AAPL", quantity=20, buy_tx_id=2,
        )
        db_session.commit()

        lots = repo.list_fifo_lots(calc["id"])
        assert len(lots) == 2
        # id 순서
        assert lots[0]["quantity"] == 30
        assert lots[1]["quantity"] == 20

    def test_insert_fifo_lot_with_warning(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx, calc = self._setup_calc(repo, db_session)

        lot = repo.insert_fifo_lot(
            calculation_id=calc["id"], sell_tx_id=sell_tx["id"],
            symbol="AAPL", quantity=50, warning="매수 내역 부족",
        )
        db_session.commit()
        assert lot["warning"] == "매수 내역 부족"

    def test_delete_fifo_lots_by_year(self, db_session):
        repo = TaxRepository(db_session)
        sell_tx, calc = self._setup_calc(repo, db_session)

        repo.insert_fifo_lot(
            calculation_id=calc["id"], sell_tx_id=sell_tx["id"],
            symbol="AAPL", quantity=50,
        )
        db_session.commit()

        deleted = repo.delete_fifo_lots_by_year(2026)
        db_session.commit()
        assert deleted == 1

        assert repo.list_fifo_lots(calc["id"]) == []

    def test_delete_fifo_lots_by_year_no_calcs(self, db_session):
        repo = TaxRepository(db_session)
        deleted = repo.delete_fifo_lots_by_year(2025)
        assert deleted == 0

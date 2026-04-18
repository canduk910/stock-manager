"""양도세 매매내역/계산 저장소 — SQLAlchemy ORM adapter.

기존 store 래퍼 패턴 (order_store.py 등)과 동일.
services/tax_service.py에서 사용.
"""

from typing import Optional

from db.repositories.tax_repo import TaxRepository
from db.session import get_session


# ── TaxTransaction CRUD ──────────────────────────────────────────────────────

def insert_transaction(**kwargs) -> dict:
    with get_session() as db:
        return TaxRepository(db).insert_transaction(**kwargs)


def list_transactions(
    year: int = None,
    symbol: str = None,
    side: str = None,
) -> list[dict]:
    with get_session() as db:
        return TaxRepository(db).list_transactions(year=year, symbol=symbol, side=side)


def get_transaction(tx_id: int) -> Optional[dict]:
    with get_session() as db:
        return TaxRepository(db).get_transaction(tx_id)


def delete_transaction(tx_id: int) -> bool:
    with get_session() as db:
        return TaxRepository(db).delete_transaction(tx_id)


def get_by_source_order_id(order_id: int) -> Optional[dict]:
    with get_session() as db:
        return TaxRepository(db).get_by_source_order_id(order_id)


def exists_by_key(symbol: str, side: str, trade_date: str, price_foreign: float, quantity: int) -> bool:
    with get_session() as db:
        return TaxRepository(db).exists_by_key(symbol, side, trade_date, price_foreign, quantity)


# ── TaxCalculation CRUD ──────────────────────────────────────────────────────

def insert_calculation(**kwargs) -> dict:
    with get_session() as db:
        return TaxRepository(db).insert_calculation(**kwargs)


def list_calculations(year: int, method: str = "FIFO", symbol: str = None) -> list[dict]:
    with get_session() as db:
        return TaxRepository(db).list_calculations(year=year, method=method, symbol=symbol)


def delete_calculations_by_year(year: int, method: str) -> int:
    with get_session() as db:
        return TaxRepository(db).delete_calculations_by_year(year, method)

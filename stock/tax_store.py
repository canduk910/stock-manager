"""양도세 매매내역/계산 저장소 — SQLAlchemy ORM adapter.

기존 store 래퍼 패턴 (order_store.py 등)과 동일.
services/tax_service.py에서 사용.

Phase 4 D.3: insert_* 는 ContextVar에서 user_id를 자동 부착.
"""

from typing import Optional

from db.repositories.tax_repo import TaxRepository
from db.session import get_session


def _ctx_user_id() -> Optional[int]:
    try:
        from routers._kis_auth import get_current_user_id
        return get_current_user_id()
    except Exception:
        return None


def _inject_user_id(kwargs: dict) -> dict:
    if kwargs.get("user_id") is None:
        uid = _ctx_user_id()
        if uid is not None:
            kwargs["user_id"] = uid
    return kwargs


# ── TaxTransaction CRUD ──────────────────────────────────────────────────────

def insert_transaction(**kwargs) -> dict:
    kwargs = _inject_user_id(kwargs)
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
    kwargs = _inject_user_id(kwargs)
    with get_session() as db:
        return TaxRepository(db).insert_calculation(**kwargs)


def list_calculations(year: int, method: str = "FIFO", symbol: str = None) -> list[dict]:
    with get_session() as db:
        return TaxRepository(db).list_calculations(year=year, method=method, symbol=symbol)


def delete_calculations_by_year(year: int, method: str) -> int:
    with get_session() as db:
        return TaxRepository(db).delete_calculations_by_year(year, method)


# ── TaxFifoLot CRUD ────────────────────────────────────────────────────────

def insert_fifo_lot(**kwargs) -> dict:
    kwargs = _inject_user_id(kwargs)
    with get_session() as db:
        return TaxRepository(db).insert_fifo_lot(**kwargs)


def list_fifo_lots(calculation_id: int) -> list[dict]:
    with get_session() as db:
        return TaxRepository(db).list_fifo_lots(calculation_id)


def delete_fifo_lots_by_year(year: int) -> int:
    with get_session() as db:
        return TaxRepository(db).delete_fifo_lots_by_year(year)

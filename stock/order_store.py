"""주문/예약주문 저장소 (~/stock-watchlist/orders.db — SQLite)."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

_WATCHLIST_DIR = Path.home() / "stock-watchlist"
_DB_PATH = _WATCHLIST_DIR / "orders.db"


def _init_db() -> None:
    _WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no        TEXT,
                org_no          TEXT,
                symbol          TEXT NOT NULL,
                symbol_name     TEXT,
                market          TEXT NOT NULL DEFAULT 'KR',
                side            TEXT NOT NULL,
                order_type      TEXT NOT NULL,
                price           REAL NOT NULL,
                quantity        INTEGER NOT NULL,
                filled_price    REAL,
                filled_quantity INTEGER DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'PLACED',
                currency        TEXT DEFAULT 'KRW',
                memo            TEXT DEFAULT '',
                placed_at       TEXT NOT NULL,
                filled_at       TEXT,
                updated_at      TEXT NOT NULL,
                kis_response    TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol          TEXT NOT NULL,
                symbol_name     TEXT,
                market          TEXT NOT NULL DEFAULT 'KR',
                side            TEXT NOT NULL,
                order_type      TEXT NOT NULL,
                price           REAL NOT NULL,
                quantity        INTEGER NOT NULL,
                condition_type  TEXT NOT NULL,
                condition_value TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'WAITING',
                result_order_no TEXT,
                memo            TEXT DEFAULT '',
                created_at      TEXT NOT NULL,
                triggered_at    TEXT,
                updated_at      TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def _conn():
    _init_db()
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── 주문 CRUD ────────────────────────────────────────────────────────────────

def insert_order(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    currency: str = "KRW",
    memo: str = "",
    order_no: str = None,
    org_no: str = None,
    kis_response: str = None,
) -> dict:
    now = _now()
    with _conn() as conn:
        cursor = conn.execute(
            """INSERT INTO orders
               (order_no, org_no, symbol, symbol_name, market, side, order_type,
                price, quantity, currency, memo, placed_at, updated_at, kis_response)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_no, org_no, symbol, symbol_name, market, side, order_type,
             price, quantity, currency, memo, now, now, kis_response),
        )
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _row_to_dict(row)


def update_order_status(
    order_id: int,
    status: str,
    *,
    filled_quantity: int = None,
    filled_price: float = None,
    order_no: str = None,
    org_no: str = None,
    kis_response: str = None,
) -> Optional[dict]:
    with _conn() as conn:
        fields = ["status = ?", "updated_at = ?"]
        values = [status, _now()]

        if filled_quantity is not None:
            fields.append("filled_quantity = ?")
            values.append(filled_quantity)
        if filled_price is not None:
            fields.append("filled_price = ?")
            values.append(filled_price)
        if order_no is not None:
            fields.append("order_no = ?")
            values.append(order_no)
        if org_no is not None:
            fields.append("org_no = ?")
            values.append(org_no)
        if kis_response is not None:
            fields.append("kis_response = ?")
            values.append(kis_response)
        if status == "FILLED":
            fields.append("filled_at = ?")
            values.append(_now())

        values.append(order_id)
        conn.execute(f"UPDATE orders SET {', '.join(fields)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _row_to_dict(row) if row else None


def get_order(order_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        return _row_to_dict(row) if row else None


def get_order_by_order_no(order_no: str, market: str = "KR") -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_no = ? AND market = ? ORDER BY id DESC LIMIT 1",
            (order_no, market),
        ).fetchone()
        return _row_to_dict(row) if row else None


def list_orders(
    symbol: str = None,
    market: str = None,
    status: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100,
) -> list[dict]:
    with _conn() as conn:
        clauses = []
        values = []
        if symbol:
            clauses.append("symbol = ?")
            values.append(symbol)
        if market:
            clauses.append("market = ?")
            values.append(market)
        if status:
            clauses.append("status = ?")
            values.append(status)
        if date_from:
            clauses.append("placed_at >= ?")
            values.append(date_from)
        if date_to:
            clauses.append("placed_at <= ?")
            values.append(date_to + "T23:59:59")

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(limit)
        rows = conn.execute(
            f"SELECT * FROM orders {where} ORDER BY id DESC LIMIT ?", values
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def list_active_orders() -> list[dict]:
    """PLACED 또는 PARTIAL 상태인 주문 목록."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status IN ('PLACED', 'PARTIAL') ORDER BY id DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


# ── 예약주문 CRUD ─────────────────────────────────────────────────────────────

def insert_reservation(
    symbol: str,
    symbol_name: str,
    market: str,
    side: str,
    order_type: str,
    price: float,
    quantity: int,
    condition_type: str,
    condition_value: str,
    memo: str = "",
) -> dict:
    now = _now()
    with _conn() as conn:
        cursor = conn.execute(
            """INSERT INTO reservations
               (symbol, symbol_name, market, side, order_type, price, quantity,
                condition_type, condition_value, memo, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, symbol_name, market, side, order_type, price, quantity,
             condition_type, condition_value, memo, now, now),
        )
        row = conn.execute("SELECT * FROM reservations WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _row_to_dict(row)


def update_reservation_status(
    res_id: int,
    status: str,
    *,
    result_order_no: str = None,
) -> Optional[dict]:
    with _conn() as conn:
        fields = ["status = ?", "updated_at = ?"]
        values = [status, _now()]
        if status == "TRIGGERED":
            fields.append("triggered_at = ?")
            values.append(_now())
        if result_order_no is not None:
            fields.append("result_order_no = ?")
            values.append(result_order_no)
        values.append(res_id)
        conn.execute(f"UPDATE reservations SET {', '.join(fields)} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_reservations(status: str = None) -> list[dict]:
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM reservations WHERE status = ? ORDER BY id DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM reservations ORDER BY id DESC").fetchall()
        return [_row_to_dict(r) for r in rows]


def get_reservation(res_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
        return _row_to_dict(row) if row else None


def delete_reservation(res_id: int) -> bool:
    with _conn() as conn:
        cursor = conn.execute("DELETE FROM reservations WHERE id = ? AND status = 'WAITING'", (res_id,))
        return cursor.rowcount > 0

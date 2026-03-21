"""시세판 별도 등록 종목 CRUD (~/stock-watchlist/market_board.db — SQLite)."""

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

_WATCHLIST_DIR = Path.home() / "stock-watchlist"
_DB_PATH = _WATCHLIST_DIR / "market_board.db"


def _init_db() -> None:
    _WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS market_board_stocks (
                code       TEXT NOT NULL,
                market     TEXT NOT NULL DEFAULT 'KR',
                name       TEXT NOT NULL,
                added_date TEXT NOT NULL,
                PRIMARY KEY (code, market)
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
    return {
        "code": row["code"],
        "market": row["market"],
        "name": row["name"],
        "added_date": row["added_date"],
    }


def all_items() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM market_board_stocks ORDER BY added_date, code"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def add_item(code: str, name: str, market: str = "KR") -> bool:
    """추가. 중복이면 False 반환."""
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO market_board_stocks (code, market, name, added_date) VALUES (?, ?, ?, ?)",
                (code, market, name, date.today().isoformat()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def remove_item(code: str, market: str = "KR") -> bool:
    """삭제. 해당 항목이 없으면 False 반환."""
    with _conn() as conn:
        cur = conn.execute(
            "DELETE FROM market_board_stocks WHERE code = ? AND market = ?",
            (code, market),
        )
        return cur.rowcount > 0

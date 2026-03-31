"""시세판 별도 등록 종목 CRUD (~/stock-watchlist/market_board.db — SQLite)."""

import sqlite3
from datetime import date

from .db_base import connect

_DB = "market_board.db"


def _create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_board_stocks (
            code       TEXT NOT NULL,
            market     TEXT NOT NULL DEFAULT 'KR',
            name       TEXT NOT NULL,
            added_date TEXT NOT NULL,
            PRIMARY KEY (code, market)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_board_order (
            code     TEXT NOT NULL,
            market   TEXT NOT NULL DEFAULT 'KR',
            position INTEGER NOT NULL,
            PRIMARY KEY (code, market)
        )
    """)
    conn.commit()


def _conn():
    return connect(_DB, _create_tables)


def _row_to_dict(row):
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


# ── 종목 순서 관리 ──────────────────────────────────────────────────────────────

def get_order() -> list[dict]:
    """순서 테이블 조회 (position ASC)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT code, market, position FROM market_board_order ORDER BY position"
        ).fetchall()
        return [{"code": r["code"], "market": r["market"], "position": r["position"]} for r in rows]


def save_order(items: list[dict]) -> None:
    """순서 전체 교체. items: [{code, market}, ...] — 인덱스가 position."""
    with _conn() as conn:
        conn.execute("DELETE FROM market_board_order")
        conn.executemany(
            "INSERT INTO market_board_order (code, market, position) VALUES (?, ?, ?)",
            [(it["code"], it["market"], i) for i, it in enumerate(items)],
        )

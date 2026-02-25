"""관심종목 목록 CRUD (~/stock-watchlist/watchlist.db — SQLite)."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Optional

_WATCHLIST_DIR = Path.home() / "stock-watchlist"
_DB_PATH = _WATCHLIST_DIR / "watchlist.db"
_JSON_PATH = _WATCHLIST_DIR / "watchlist.json"


def _init_db() -> None:
    """DB 파일이 없으면 생성하고 테이블을 초기화한다. JSON 파일이 있으면 마이그레이션."""
    _WATCHLIST_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_DB_PATH) as conn:
        # code만 PK인 구버전 테이블이 있는 경우를 위해 임시 테이블로 마이그레이션
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                code       TEXT NOT NULL,
                market     TEXT NOT NULL DEFAULT 'KR',
                name       TEXT NOT NULL,
                added_date TEXT NOT NULL,
                memo       TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (code, market)
            )
        """)
        # 기존 테이블에 market 컬럼이 없는 경우 추가 (안전한 마이그레이션)
        try:
            conn.execute("ALTER TABLE watchlist ADD COLUMN market TEXT NOT NULL DEFAULT 'KR'")
        except sqlite3.OperationalError:
            pass  # 이미 존재하면 무시
        conn.commit()

    # 기존 JSON 파일이 있고 DB가 비어있으면 마이그레이션
    if _JSON_PATH.exists():
        try:
            items = json.loads(_JSON_PATH.read_text(encoding="utf-8"))
            if not items:
                return
            with sqlite3.connect(_DB_PATH) as conn:
                existing = {row[0] for row in conn.execute("SELECT code FROM watchlist")}
                migrated = 0
                for item in items:
                    if item.get("code") not in existing:
                        conn.execute(
                            "INSERT OR IGNORE INTO watchlist (code, market, name, added_date, memo) VALUES (?, ?, ?, ?, ?)",
                            (item["code"], "KR", item["name"], item.get("added_date", date.today().isoformat()), item.get("memo", "")),
                        )
                        migrated += 1
                conn.commit()
            if migrated:
                # 마이그레이션 완료 후 JSON 파일을 백업으로 보관
                _JSON_PATH.rename(_JSON_PATH.with_suffix(".json.bak"))
                print(f"[store] JSON → SQLite 마이그레이션 완료 ({migrated}개). 백업: watchlist.json.bak")
        except Exception as e:
            print(f"[store] JSON 마이그레이션 실패 (무시): {e}")


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
        "market": row["market"] if "market" in row.keys() else "KR",
        "name": row["name"],
        "added_date": row["added_date"],
        "memo": row["memo"],
    }


def all_items() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY added_date, code").fetchall()
        return [_row_to_dict(r) for r in rows]


def get_item(code: str, market: str = "KR") -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM watchlist WHERE code = ? AND market = ?", (code, market)).fetchone()
        return _row_to_dict(row) if row else None


def add_item(code: str, name: str, memo: str = "", market: str = "KR") -> bool:
    """이미 존재하면 False, 새로 추가하면 True."""
    with _conn() as conn:
        existing = conn.execute("SELECT 1 FROM watchlist WHERE code = ? AND market = ?", (code, market)).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT INTO watchlist (code, market, name, added_date, memo) VALUES (?, ?, ?, ?, ?)",
            (code, market, name, date.today().isoformat(), memo),
        )
        return True


def remove_item(code: str, market: str = "KR") -> bool:
    with _conn() as conn:
        cursor = conn.execute("DELETE FROM watchlist WHERE code = ? AND market = ?", (code, market))
        return cursor.rowcount > 0


def update_memo(code: str, memo: str, market: str = "KR") -> bool:
    with _conn() as conn:
        cursor = conn.execute("UPDATE watchlist SET memo = ? WHERE code = ? AND market = ?", (memo, code, market))
        return cursor.rowcount > 0

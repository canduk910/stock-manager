"""매크로 GPT 결과 일일 캐시 (~/stock-watchlist/macro.db).

당일(KST) 이미 GPT 결과가 있으면 재호출하지 않는다.
카테고리 예: 'nyt_translation', 'investor:Warren Buffett'
"""
from __future__ import annotations

import json
import random
from datetime import timedelta
from typing import Optional

from .db_base import KST, connect, now_kst

_DB = "macro.db"


def _create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS macro_gpt_cache (
            category   TEXT NOT NULL,
            date_kst   TEXT NOT NULL,
            result     TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (category, date_kst)
        )
    """)


def _conn():
    return connect(_DB, _create_tables)


def _today_kst() -> str:
    return now_kst().strftime("%Y-%m-%d")


def _maybe_cleanup(conn):
    """~5% 확률로 30일 이전 데이터 삭제."""
    if random.random() < 0.05:
        cutoff = (now_kst() - timedelta(days=30)).strftime("%Y-%m-%d")
        conn.execute("DELETE FROM macro_gpt_cache WHERE date_kst < ?", (cutoff,))


def get_today(category: str) -> Optional[any]:
    """당일(KST) GPT 결과 조회. 없으면 None."""
    today = _today_kst()
    with _conn() as con:
        _maybe_cleanup(con)
        row = con.execute(
            "SELECT result FROM macro_gpt_cache WHERE category=? AND date_kst=?",
            (category, today),
        ).fetchone()
    if not row:
        return None
    return json.loads(row["result"])


def save_today(category: str, result) -> None:
    """당일(KST) GPT 결과 저장 (upsert)."""
    today = _today_kst()
    now = now_kst().isoformat()
    with _conn() as con:
        con.execute(
            """INSERT INTO macro_gpt_cache (category, date_kst, result, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(category, date_kst) DO UPDATE SET
                   result=excluded.result, created_at=excluded.created_at""",
            (category, today, json.dumps(result, ensure_ascii=False), now),
        )

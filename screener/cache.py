import json
import os
import sqlite3
from datetime import datetime

_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "screener_cache.db"
)


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
        """
    )
    return conn


def get_cached(key: str):
    """캐시에서 데이터 조회. 없으면 None 반환."""
    try:
        conn = _get_conn()
        row = conn.execute("SELECT value FROM cache WHERE key = ?", (key,)).fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return None


def set_cached(key: str, value) -> None:
    """데이터를 캐시에 저장."""
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, fetched_at) VALUES (?, ?, ?)",
            (key, json.dumps(value, ensure_ascii=False), datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def clear_cache() -> None:
    """캐시 전체 삭제."""
    try:
        conn = _get_conn()
        conn.execute("DELETE FROM cache")
        conn.commit()
        conn.close()
    except Exception:
        pass
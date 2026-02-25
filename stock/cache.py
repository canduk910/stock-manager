"""24시간 TTL SQLite 캐시 (~/stock-watchlist/cache.db)."""

import json
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def _sanitize(obj):
    """재귀적으로 NaN/Inf를 None으로 변환 (JSON 직렬화 안전 보장)."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj

_CACHE_DIR = Path.home() / "stock-watchlist"
_DB_PATH = _CACHE_DIR / "cache.db"


def _conn() -> sqlite3.Connection:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(_DB_PATH)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key     TEXT PRIMARY KEY,
            value   TEXT NOT NULL,
            expires TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


def get_cached(key: str):
    """캐시 조회. 만료됐거나 없으면 None 반환. NaN 값은 None으로 정제."""
    try:
        with _conn() as con:
            row = con.execute(
                "SELECT value, expires FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if not row:
            return None
        value, expires = row
        if datetime.utcnow() > datetime.fromisoformat(expires):
            return None
        return _sanitize(json.loads(value))
    except Exception:
        return None


def set_cached(key: str, value, ttl_hours: int = 24) -> None:
    """데이터를 캐시에 저장. NaN/Inf는 None으로 변환 후 저장."""
    expires = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()
    try:
        sanitized = _sanitize(value)
        with _conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
                (key, json.dumps(sanitized, ensure_ascii=False), expires),
            )
    except Exception:
        pass


def delete_cached(key: str) -> None:
    try:
        with _conn() as con:
            con.execute("DELETE FROM cache WHERE key = ?", (key,))
    except Exception:
        pass


def delete_prefix(prefix: str) -> None:
    """접두사로 시작하는 캐시 키 일괄 삭제."""
    try:
        with _conn() as con:
            con.execute("DELETE FROM cache WHERE key LIKE ?", (f"{prefix}%",))
    except Exception:
        pass

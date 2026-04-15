"""SQLite 저장소 공통 유틸리티.

모든 store 모듈이 공유하는 DB 디렉토리, 연결 contextmanager, 초기화 관리, KST 시간.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

# KST 유틸은 db/utils.py가 정의 원본. 여기서는 re-export (기존 caller 호환).
from db.utils import KST, now_kst, now_kst_iso  # noqa: F401

DB_DIR = Path.home() / "stock-watchlist"

_initialized: set[str] = set()


@contextmanager
def connect(db_name: str, init_fn=None):
    """SQLite 연결 contextmanager.

    - DB_DIR 자동 생성
    - row_factory = sqlite3.Row
    - init_fn(conn) — 최초 1회만 호출 (테이블 생성 등)
    - yield 후 자동 commit, finally close
    """
    DB_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DB_DIR / db_name
    conn = sqlite3.connect(db_path, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    if init_fn and db_name not in _initialized:
        init_fn(conn)
        _initialized.add(db_name)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """sqlite3.Row → dict 변환."""
    return {k: row[k] for k in row.keys()}

"""AI자문 종목 목록 + 캐시 + 리포트 CRUD.

DB 위치: ~/stock-watchlist/advisory.db
"""

import json
import sqlite3
from datetime import datetime
from typing import Optional

from .db_base import connect, row_to_dict

_DB = "advisory.db"


def _create_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS advisory_stocks (
            code       TEXT NOT NULL,
            market     TEXT NOT NULL DEFAULT 'KR',
            name       TEXT NOT NULL,
            added_date TEXT NOT NULL,
            memo       TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (code, market)
        );

        CREATE TABLE IF NOT EXISTS advisory_cache (
            code        TEXT NOT NULL,
            market      TEXT NOT NULL DEFAULT 'KR',
            updated_at  TEXT NOT NULL,
            fundamental TEXT,
            technical   TEXT,
            PRIMARY KEY (code, market)
        );

        CREATE TABLE IF NOT EXISTS advisory_reports (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            code         TEXT NOT NULL,
            market       TEXT NOT NULL DEFAULT 'KR',
            generated_at TEXT NOT NULL,
            model        TEXT NOT NULL,
            report       TEXT NOT NULL
        );
    """)


def _conn():
    return connect(_DB, _create_tables)


# ── 자문종목 CRUD ─────────────────────────────────────────────────────────────

def add_stock(code: str, market: str, name: str, memo: str = "") -> bool:
    """종목 추가. 이미 존재하면 False."""
    try:
        with _conn() as con:
            con.execute(
                "INSERT INTO advisory_stocks (code, market, name, added_date, memo) VALUES (?,?,?,?,?)",
                (code.upper(), market.upper(), name, datetime.now().isoformat(), memo),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def remove_stock(code: str, market: str) -> bool:
    """종목 삭제. 삭제된 행이 있으면 True."""
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM advisory_stocks WHERE code=? AND market=?",
            (code.upper(), market.upper()),
        )
        return cur.rowcount > 0


def all_stocks() -> list[dict]:
    """전체 자문종목 목록 (added_date 역순)."""
    with _conn() as con:
        rows = con.execute(
            "SELECT code, market, name, added_date, memo FROM advisory_stocks ORDER BY added_date DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_stock(code: str, market: str) -> Optional[dict]:
    """단일 종목 조회."""
    with _conn() as con:
        row = con.execute(
            "SELECT code, market, name, added_date, memo FROM advisory_stocks WHERE code=? AND market=?",
            (code.upper(), market.upper()),
        ).fetchone()
    return dict(row) if row else None


# ── 캐시 CRUD ─────────────────────────────────────────────────────────────────

def save_cache(code: str, market: str, fundamental: dict, technical: dict) -> None:
    """분석 데이터 캐시 저장 (upsert)."""
    with _conn() as con:
        con.execute(
            """INSERT INTO advisory_cache (code, market, updated_at, fundamental, technical)
               VALUES (?,?,?,?,?)
               ON CONFLICT(code, market) DO UPDATE SET
                   updated_at=excluded.updated_at,
                   fundamental=excluded.fundamental,
                   technical=excluded.technical""",
            (
                code.upper(),
                market.upper(),
                datetime.now().isoformat(),
                json.dumps(fundamental, ensure_ascii=False),
                json.dumps(technical, ensure_ascii=False),
            ),
        )


def get_cache(code: str, market: str) -> Optional[dict]:
    """캐시 조회. 없으면 None."""
    with _conn() as con:
        row = con.execute(
            "SELECT code, market, updated_at, fundamental, technical FROM advisory_cache WHERE code=? AND market=?",
            (code.upper(), market.upper()),
        ).fetchone()
    if not row:
        return None
    return {
        "code": row["code"],
        "market": row["market"],
        "updated_at": row["updated_at"],
        "fundamental": json.loads(row["fundamental"] or "{}"),
        "technical": json.loads(row["technical"] or "{}"),
    }


# ── 리포트 CRUD ───────────────────────────────────────────────────────────────

def save_report(code: str, market: str, model: str, report: dict) -> int:
    """AI 리포트 저장. 생성된 ID 반환."""
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO advisory_reports (code, market, generated_at, model, report) VALUES (?,?,?,?,?)",
            (
                code.upper(),
                market.upper(),
                datetime.now().isoformat(),
                model,
                json.dumps(report, ensure_ascii=False),
            ),
        )
        return cur.lastrowid


def get_report_history(code: str, market: str, limit: int = 20) -> list[dict]:
    """AI 리포트 히스토리 목록 (최신순, 본문 제외)."""
    with _conn() as con:
        rows = con.execute(
            """SELECT id, code, market, generated_at, model
               FROM advisory_reports WHERE code=? AND market=?
               ORDER BY id DESC LIMIT ?""",
            (code.upper(), market.upper(), limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_report_by_id(report_id: int) -> Optional[dict]:
    """특정 ID의 AI 리포트 조회."""
    with _conn() as con:
        row = con.execute(
            "SELECT id, code, market, generated_at, model, report FROM advisory_reports WHERE id=?",
            (report_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "code": row["code"],
        "market": row["market"],
        "generated_at": row["generated_at"],
        "model": row["model"],
        "report": json.loads(row["report"] or "{}"),
    }


def get_latest_report(code: str, market: str) -> Optional[dict]:
    """최신 AI 리포트 조회."""
    with _conn() as con:
        row = con.execute(
            """SELECT id, code, market, generated_at, model, report
               FROM advisory_reports WHERE code=? AND market=?
               ORDER BY id DESC LIMIT 1""",
            (code.upper(), market.upper()),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "code": row["code"],
        "market": row["market"],
        "generated_at": row["generated_at"],
        "model": row["model"],
        "report": json.loads(row["report"] or "{}"),
    }

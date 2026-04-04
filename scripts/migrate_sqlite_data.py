#!/usr/bin/env python3
"""Migrate data from 6 legacy SQLite DBs into unified app.db (SQLAlchemy).

Usage:
    python scripts/migrate_sqlite_data.py

This script:
1. Backs up existing app.db (if any) to app.db.bak
2. Runs Alembic upgrade head to ensure schema is current
3. Reads each legacy DB and inserts rows into app.db with ID preservation (F5)
4. Reports row counts per table
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from config import DATABASE_URL
from stock.db_base import DB_DIR

# Target app.db path (extracted from DATABASE_URL)
if DATABASE_URL.startswith("sqlite:///"):
    APP_DB_PATH = Path(DATABASE_URL.replace("sqlite:///", ""))
else:
    print(f"[ERROR] DATABASE_URL is not SQLite: {DATABASE_URL}")
    print("        Data migration only supports SQLite -> SQLite.")
    sys.exit(1)

# Legacy DB files
LEGACY_DBS = {
    "watchlist.db": ["watchlist", "watchlist_order"],
    "orders.db": ["orders", "reservations"],
    "advisory.db": ["advisory_stocks", "advisory_cache", "advisory_reports", "portfolio_reports"],
    "market_board.db": ["market_board_stocks", "market_board_order"],
    "stock_info.db": ["stock_info"],
    "macro.db": ["macro_gpt_cache"],
}

# JSON columns that need json.loads for SA JSON type
JSON_COLUMNS = {
    "advisory_cache": ["fundamental", "technical"],
    "advisory_reports": ["report"],
    "portfolio_reports": ["report"],
    "macro_gpt_cache": ["result"],
}


def _read_legacy_table(db_path: Path, table_name: str) -> tuple[list[str], list[tuple]]:
    """Read all rows from a legacy table. Returns (column_names, rows)."""
    if not db_path.exists():
        return [], []
    try:
        conn = sqlite3.connect(str(db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        if not rows:
            conn.close()
            return [], []
        columns = rows[0].keys()
        data = [tuple(row[c] for c in columns) for row in rows]
        conn.close()
        return list(columns), data
    except sqlite3.OperationalError as e:
        print(f"  [SKIP] {db_path.name}/{table_name}: {e}")
        return [], []


def _deserialize_json(columns: list[str], rows: list[tuple], table_name: str) -> list[tuple]:
    """Deserialize JSON TEXT columns to Python dicts for SQLAlchemy JSON type."""
    json_cols = JSON_COLUMNS.get(table_name)
    if not json_cols:
        return rows
    json_indices = [i for i, c in enumerate(columns) if c in json_cols]
    if not json_indices:
        return rows
    new_rows = []
    for row in rows:
        row_list = list(row)
        for idx in json_indices:
            val = row_list[idx]
            if isinstance(val, str):
                try:
                    row_list[idx] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    row_list[idx] = {}
            elif val is None:
                row_list[idx] = {}
        new_rows.append(tuple(row_list))
    return new_rows


def _insert_into_app_db(app_conn: sqlite3.Connection, table_name: str, columns: list[str], rows: list[tuple]):
    """Insert rows into app.db, preserving IDs (F5)."""
    if not rows:
        return 0
    # Serialize JSON columns back to TEXT for SQLite storage
    json_cols = JSON_COLUMNS.get(table_name)
    if json_cols:
        json_indices = [i for i, c in enumerate(columns) if c in json_cols]
        new_rows = []
        for row in rows:
            row_list = list(row)
            for idx in json_indices:
                val = row_list[idx]
                if isinstance(val, (dict, list)):
                    row_list[idx] = json.dumps(val, ensure_ascii=False)
            new_rows.append(tuple(row_list))
        rows = new_rows

    placeholders = ", ".join(["?"] * len(columns))
    col_str = ", ".join(columns)
    sql = f"INSERT OR IGNORE INTO {table_name} ({col_str}) VALUES ({placeholders})"
    app_conn.executemany(sql, rows)
    return len(rows)


def main():
    print("=" * 60)
    print("SQLAlchemy Data Migration: Legacy DBs -> app.db")
    print("=" * 60)
    print(f"  Source directory: {DB_DIR}")
    print(f"  Target database: {APP_DB_PATH}")
    print()

    # Step 1: Backup existing app.db
    if APP_DB_PATH.exists():
        backup_path = APP_DB_PATH.with_suffix(".db.pre_migration_bak")
        shutil.copy2(APP_DB_PATH, backup_path)
        print(f"[BACKUP] app.db -> {backup_path.name}")

    # Step 2: Run Alembic upgrade
    print("[ALEMBIC] Running upgrade head...")
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    if result.returncode != 0:
        print(f"[ERROR] Alembic upgrade failed:\n{result.stderr}")
        sys.exit(1)
    print("[ALEMBIC] Schema up to date.")
    print()

    # Step 3: Migrate data
    app_conn = sqlite3.connect(str(APP_DB_PATH), timeout=10)
    app_conn.execute("PRAGMA journal_mode=WAL")

    total_migrated = 0
    for db_name, tables in LEGACY_DBS.items():
        db_path = DB_DIR / db_name
        if not db_path.exists():
            print(f"[SKIP] {db_name} not found")
            continue
        print(f"[MIGRATE] {db_name}")
        for table in tables:
            columns, rows = _read_legacy_table(db_path, table)
            if not rows:
                print(f"  {table}: 0 rows (empty or missing)")
                continue
            count = _insert_into_app_db(app_conn, table, columns, rows)
            total_migrated += count
            print(f"  {table}: {count} rows migrated")

    app_conn.commit()
    app_conn.close()

    print()
    print(f"[DONE] Total rows migrated: {total_migrated}")
    print()

    # Step 4: Backup legacy DBs (rename to .bak)
    print("[BACKUP] Renaming legacy DB files...")
    for db_name in LEGACY_DBS:
        db_path = DB_DIR / db_name
        if db_path.exists():
            bak_path = db_path.with_suffix(".db.bak")
            if not bak_path.exists():
                shutil.copy2(db_path, bak_path)
                print(f"  {db_name} -> {bak_path.name}")
            else:
                print(f"  {db_name}: backup already exists, skipping")

    print()
    print("Migration complete. Legacy .db.bak files preserved for rollback.")
    print("To verify: sqlite3 ~/stock-watchlist/app.db '.tables'")


if __name__ == "__main__":
    main()

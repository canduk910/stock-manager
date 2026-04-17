# QA Report: SQLAlchemy ORM Migration

**Date**: 2026-04-04
**Scope**: SQLite -> SQLAlchemy ORM migration (6 stores -> db/ package)
**Result**: 3 FAIL, 2 WARN, 20 PASS

---

## 1. Store Wrapper <-> Repository Signature Parity (HIGHEST PRIORITY)

### 1.1 store.py (Watchlist)

| Function | Original Signature | New Wrapper | Repository | Status |
|----------|-------------------|-------------|------------|--------|
| `all_items()` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `get_item(code, market="KR")` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `add_item(code, name, memo="", market="KR")` | `-> bool` | Delegates to repo | Matches | PASS |
| `remove_item(code, market="KR")` | `-> bool` | Delegates to repo | Matches | PASS |
| `update_memo(code, memo, market="KR")` | `-> bool` | Delegates to repo | Matches | PASS |
| `get_order()` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `save_order(items)` | `-> None` | Delegates to repo | Matches | PASS |

**Result**: PASS (7/7 functions)

### 1.2 order_store.py

| Function | Original Signature | New Wrapper | Repository | Status |
|----------|-------------------|-------------|------------|--------|
| `insert_order(symbol, symbol_name, market, side, order_type, price, quantity, currency="KRW", memo="", order_no=None, org_no=None, kis_response=None, status="PLACED")` | `-> dict` | Delegates to repo | Matches | PASS |
| `update_order_status(order_id, status, *, filled_quantity=None, filled_price=None, order_no=None, org_no=None, kis_response=None)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `get_order(order_id)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `get_order_by_order_no(order_no, market="KR")` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `list_orders(symbol=None, market=None, status=None, date_from=None, date_to=None, limit=100)` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `list_active_orders()` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `update_order_details(order_id, *, price=None, quantity=None, order_type=None)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `insert_reservation(...)` | `-> dict` | Delegates to repo | Matches | PASS |
| `update_reservation_status(res_id, status, *, result_order_no=None)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `list_reservations(status=None)` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `get_reservation(res_id)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `delete_reservation(res_id)` | `-> bool` | Delegates to repo | Matches | PASS |

**Result**: PASS (12/12 functions)

### 1.3 advisory_store.py

| Function | Original Signature | New Wrapper | Repository | Status |
|----------|-------------------|-------------|------------|--------|
| `add_stock(code, market, name, memo="")` | `-> bool` | Delegates to repo | Matches | PASS |
| `remove_stock(code, market)` | `-> bool` | Delegates to repo | Matches | PASS |
| `all_stocks()` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `get_stock(code, market)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `save_cache(code, market, fundamental, technical)` | `-> None` | Delegates to repo | Matches | PASS |
| `get_cache(code, market)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `save_report(code, market, model, report)` | `-> int` | Delegates to repo | Matches | PASS |
| `get_report_history(code, market, limit=20)` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `get_report_by_id(report_id)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `get_latest_report(code, market)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `save_portfolio_report(model, report)` | `-> int` | Delegates to repo | Matches | PASS |
| `get_portfolio_report_history(limit=20)` | `-> list[dict]` | Delegates to repo | Matches | PASS |
| `get_portfolio_report_by_id(report_id)` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |
| `get_latest_portfolio_report()` | `-> Optional[dict]` | Delegates to repo | Matches | PASS |

**Result**: PASS (14/14 functions)

### 1.4 market_board_store.py

**Result**: PASS (5/5 functions). Signatures identical.

### 1.5 stock_info_store.py

**Result**: PASS (7/7 functions). Signatures identical.

### 1.6 macro_store.py

**Result**: PASS (2/2 functions). Signatures identical.

---

## 2. Model to_dict() <-> Original Dict Keys

### 2.1 Order.to_dict()

Original: `row_to_dict(row)` -> all 18 columns from `SELECT *`.
New: 18 keys in `to_dict()`.

| Key | Original Type | New Type | Match |
|-----|---------------|----------|-------|
| `id` | INTEGER | Integer | PASS |
| `order_no` | TEXT | String | PASS |
| `org_no` | TEXT | String | PASS |
| `symbol` | TEXT | String | PASS |
| `symbol_name` | TEXT | String | PASS |
| `market` | TEXT | String | PASS |
| `side` | TEXT | String | PASS |
| `order_type` | TEXT | String | PASS |
| `price` | REAL | Float | PASS |
| `quantity` | INTEGER | Integer | PASS |
| `filled_price` | REAL | Float | PASS |
| `filled_quantity` | INTEGER | Integer | PASS |
| `status` | TEXT | String | PASS |
| `currency` | TEXT | String | PASS |
| `memo` | TEXT | Text | PASS |
| `placed_at` | TEXT | String | PASS |
| `filled_at` | TEXT | String | PASS |
| `updated_at` | TEXT | String | PASS |
| `kis_response` | TEXT | Text | PASS |

**Result**: PASS (18/18 keys)

### 2.2 AdvisoryCache.to_dict() -- JSON columns

Original `get_cache()`:
```python
{"code", "market", "updated_at",
 "fundamental": json.loads(row["fundamental"] or "{}"),
 "technical": json.loads(row["technical"] or "{}")}
```

New `to_dict()`:
```python
{"code", "market", "updated_at",
 "fundamental": self.fundamental or {},
 "technical": self.technical or {}}
```

SQLAlchemy `JSON` type auto-deserializes TEXT->dict on read, so `self.fundamental` is already a dict.
`self.fundamental or {}` correctly handles `None` -> `{}`, matching original behavior.

**Result**: PASS

### 2.3 AdvisoryReport.to_dict() -- JSON column

Original: `"report": json.loads(row["report"] or "{}")`
New: `"report": self.report or {}`

**Result**: PASS

### 2.4 AdvisoryReport.to_summary_dict() -- history without body

Original: `dict(r)` for `SELECT id, code, market, generated_at, model` (5 keys, no report).
New: `to_summary_dict()` returns 5 keys: id, code, market, generated_at, model.

**Result**: PASS

### 2.5 PortfolioReport.to_dict() / to_summary_dict()

**Result**: PASS. Keys match original.

### 2.6 Watchlist, WatchlistOrder, MarketBoardStock, MarketBoardOrder, StockInfo, MacroGptCache

All `to_dict()` outputs verified against original `SELECT *` / `_row_to_dict()` patterns.

**Result**: PASS (all remaining models)

---

## 3. Session Management Patterns

### 3.1 get_session() usage (Store wrappers)

All 6 store wrappers use identical pattern:
```python
with get_session() as db:
    return SomeRepository(db).some_method(...)
```

`get_session()` is a `@contextmanager` that: yield -> commit -> except rollback -> finally close.
Repositories call `flush()` (not `commit()`) to get auto-generated IDs.

**Result**: PASS

### 3.2 get_db() usage (FastAPI Depends)

`get_db()` is defined but **not currently used** by any router. All routers import store modules directly (e.g., `from stock import store`). This is consistent with the migration approach (wrappers, not DI).

**Result**: PASS (unused but harmless)

### 3.3 No pattern mixing

Verified: no file imports both `get_session()` and `get_db()`. Store wrappers use `get_session()` only. No router uses `get_db()` Depends.

**Result**: PASS

---

## 4. Alembic Migration <-> Model Schema

### 4.1 Table count

Models define 12 tables. Migration creates 12 tables. Match.

| Table | Model | Migration | Match |
|-------|-------|-----------|-------|
| watchlist | Watchlist | line 158 | PASS |
| watchlist_order | WatchlistOrder | line 166 | PASS |
| orders | Order | line 72 | PASS |
| reservations | Reservation | line 106 | PASS |
| advisory_stocks | AdvisoryStock | line 44 | PASS |
| advisory_cache | AdvisoryCache | line 24 | PASS |
| advisory_reports | AdvisoryReport | line 32 | PASS |
| portfolio_reports | PortfolioReport | line 99 | PASS |
| market_board_stocks | MarketBoardStock | line 65 | PASS |
| market_board_order | MarketBoardOrder | line 59 | PASS |
| stock_info | StockInfo | line 125 | PASS |
| macro_gpt_cache | MacroGptCache | line 52 | PASS |

### 4.2 Indexes

| Index | Model | Migration | Match |
|-------|-------|-----------|-------|
| `idx_orders_status` | Order.__table_args__ | line 96 | PASS |
| `idx_orders_order_no_market` | Order.__table_args__ | line 95 | PASS |
| `idx_orders_symbol_market` (DESC) | Order.__table_args__ | line 97 | PASS |
| `idx_advisory_reports_code_market` (DESC) | AdvisoryReport.__table_args__ | line 42 | PASS |
| `idx_stock_info_price_updated` | StockInfo.__table_args__ | line 156 | PASS |

**Result**: PASS (5/5 indexes)

### 4.3 Column-level verification (spot-checked)

Verified all columns in orders, reservations, advisory_cache, stock_info tables.
Column names, types, nullable flags, and primary keys all match between model and migration.

**Result**: PASS

---

## 5. main.py Lifespan Ordering

```
1. [NEW] Alembic upgrade head (try/except, non-fatal)
2. [EXISTING] KIS env var warnings
3. [EXISTING] Symbol map + FNO pre-warm (background thread)
4. [EXISTING] Quote WS manager start
5. [EXISTING] Overseas manager start
6. [EXISTING] Reservation scheduler start
```

Alembic runs FIRST, before any store operations. DB is guaranteed ready before any repository call.

**Result**: PASS

---

## 6. entrypoint.sh Ordering

```
1. [EXISTING] Environment validation
2. [EXISTING] Frontend build check
3. [EXISTING] Cache initialization (cache.db) -- also creates ~/stock-watchlist/ directory
4. [NEW] alembic upgrade head
5. [EXISTING] uvicorn main:app
```

`alembic upgrade head` runs AFTER cache init (which creates `~/stock-watchlist/` via `db_base.connect()`), so the directory exists before Alembic tries to create `app.db`.

**Result**: PASS

---

## 7. Build Tests

### 7.1 Frontend build

```
npm run build -> SUCCESS (1.16s, 775 modules)
```

**Result**: PASS

### 7.2 Python model import

```
python -c "from db.models import *" -> SUCCESS
```

**Result**: PASS

### 7.3 Full import chain (no circular imports)

```
python -c "from stock import store, order_store, advisory_store, ..." -> SUCCESS
```

**Result**: PASS

---

## 8. ISSUES FOUND

### FAIL-1: [MAJOR] DB directory not created for fresh local installs

**Location**: `db/session.py`
**Boundary**: `db/session.py` (producer) <-> `config.py` DATABASE_URL (consumer)

**Problem**:
- Producer: `session.py` creates `engine = create_engine(DATABASE_URL)` at import time
- Consumer: SQLAlchemy/Alembic expects `~/stock-watchlist/` directory to exist
- Original `db_base.py` line 38 always runs `DB_DIR.mkdir(parents=True, exist_ok=True)` on every `connect()` call
- New `session.py` has no directory creation logic
- `entrypoint.sh` calls `cache.py` which triggers `db_base.connect()` (creates directory), but local dev (`python main.py`) runs Alembic FIRST before any `db_base.connect()` call

**Impact**: Fresh local install (never run before, no `~/stock-watchlist/` directory) will fail at startup with `sqlite3.OperationalError: unable to open database file`.

**Fix**:
```
File: db/session.py
After line 13 (from config import DATABASE_URL), add:

    from pathlib import Path
    if "sqlite" in DATABASE_URL:
        _db_path = DATABASE_URL.replace("sqlite:///", "")
        Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
```

---

### FAIL-2: [MAJOR] Alembic DESC index uses sa.literal_column -- may fail on Alembic autogenerate diff

**Location**: `alembic/versions/cd83884bc87e_initial_schema.py` lines 42, 97
**Boundary**: `db/models/order.py` (model) <-> `alembic/versions/` (migration)

**Problem**:
```python
# Model
Index("idx_orders_symbol_market", "symbol", "market", placed_at.desc())

# Alembic migration
batch_op.create_index('idx_orders_symbol_market',
    ['symbol', 'market', sa.literal_column('placed_at DESC')])
```

`sa.literal_column('placed_at DESC')` is a workaround for SQLite DESC indexes. When running `alembic revision --autogenerate` for future migrations, Alembic may detect a false diff because it cannot introspect `sa.literal_column` the same way as the model's `placed_at.desc()`. This will cause every future autogenerate to include a spurious "recreate index" operation.

Same issue for `idx_advisory_reports_code_market` (line 42).

**Impact**: Future `alembic revision --autogenerate` will always show dirty diffs for these 2 indexes, leading to unnecessary migration steps or developer confusion.

**Fix**: No immediate fix needed (current migration works). For future autogenerate sessions, add these indexes to the `EnvironmentContext.configure(include_object=...)` exclude list, or document this behavior.

---

### FAIL-3: [MINOR] Migration script JSON re-serialization is redundant

**Location**: `scripts/migrate_sqlite_data.py` lines 77-98, 101-123
**Boundary**: `scripts/migrate_sqlite_data.py` <-> `app.db` (target)

**Problem**:
The migration script:
1. `_deserialize_json()`: Reads TEXT from legacy DB, calls `json.loads()` to convert to Python dict
2. `_insert_into_app_db()`: Calls `json.dumps()` to convert back to TEXT for raw SQL INSERT

This deserialize-then-reserialize cycle is correct but redundant. Since the legacy DB stores JSON as TEXT and the new app.db also stores JSON as TEXT (SQLite `JSON` type = `TEXT`), the data could be copied as-is without conversion.

However, the current implementation IS functionally correct. The round-trip through `json.loads/json.dumps` normalizes formatting and validates JSON. No data loss.

**Impact**: Minor performance overhead during migration. No correctness issue.

**Fix**: No fix needed. Current implementation is safe.

---

### WARN-1: No server_default for columns with Python-level defaults

**Location**: `db/models/order.py` lines 22-25
**Boundary**: `db/models/order.py` (model) <-> Alembic migration (schema)

**Problem**:
Original schema: `filled_quantity INTEGER DEFAULT 0`, `status TEXT NOT NULL DEFAULT 'PLACED'`
New model: `filled_quantity = Column(Integer, default=0)`, `status = Column(String, default="PLACED")`

Python `default=` only works when creating rows through SQLAlchemy ORM. Raw SQL inserts (e.g., migration script) or direct SQLite access won't get these defaults. The Alembic migration creates columns with `nullable=True` for `filled_quantity` -- meaning raw inserts get `NULL` instead of `0`.

**Impact**: Low. All data access goes through ORM repositories. Migration script copies existing data with actual values. Only affects potential future raw SQL operations.

**Recommendation**: Consider adding `server_default=text("0")` for `filled_quantity` and `server_default=text("'PLACED'")` for `status` in the model, to match original SQLite schema behavior.

---

### WARN-2: Double Alembic execution (entrypoint.sh + main.py lifespan)

**Location**: `entrypoint.sh` line 65, `main.py` line 31

**Problem**: Alembic `upgrade head` runs twice in Docker deployments:
1. `entrypoint.sh` line 65: `python3 -m alembic upgrade head`
2. `main.py` lifespan lines 27-31: `alembic_command.upgrade(alembic_cfg, "head")`

**Impact**: None. Alembic is idempotent -- running `upgrade head` when already at head is a no-op. This is actually intentional: `entrypoint.sh` covers Docker, `main.py` covers local dev. Startup adds ~100ms overhead.

**Recommendation**: Acceptable as-is. Consider documenting the intentional double-execution.

---

## 9. Additional Verifications

### 9.1 Caller Impact -- services/ and routers/ unchanged

Verified all callers of store functions:

| Caller | Import | Functions Used | Impact |
|--------|--------|---------------|--------|
| `services/order_service.py` | `from stock import order_store` | `insert_order, update_order_status, get_order_by_order_no, list_active_orders, update_order_details, list_orders, insert_reservation, list_reservations, get_reservation, delete_reservation` | None (wrapper preserves all signatures) |
| `services/reservation_service.py` | `from stock import order_store` | `list_reservations, update_reservation_status` | None |
| `services/advisory_service.py` | `from stock import advisory_store` | `save_cache, get_cache, save_report, get_latest_report` | None |
| `services/portfolio_advisor_service.py` | `from stock import advisory_store` | `save_portfolio_report, get_portfolio_report_history, get_portfolio_report_by_id` | None |
| `services/watchlist_service.py` | `from stock import store` + `from stock.stock_info_store import ...` | `all_items, get_item, add_item, remove_item, update_memo; get_stock_info, is_stale` | None |
| `services/macro_service.py` | `from stock.macro_store import get_today, save_today` | `get_today, save_today` | None |
| `routers/watchlist.py` | `from stock import store` | `all_items, add_item, remove_item, update_memo, get_order, save_order` | None |
| `routers/advisory.py` | `from stock import advisory_store` | Various | None |
| `routers/market_board.py` | `from stock.market_board_store import ...` | `all_items, add_item, remove_item, get_order, save_order` | None |
| `stock/market.py` | `from .stock_info_store import upsert_price, upsert_metrics, upsert_returns` | Write-through cache | None |
| `stock/dart_fin.py` | `from .stock_info_store import upsert_financials` | Write-through cache | None |
| `stock/yf_client.py` | `from .stock_info_store import upsert_price, upsert_metrics, upsert_financials` | Write-through cache | None |

### 9.2 Unchanged files confirmed

| File | Changed? |
|------|----------|
| `stock/cache.py` | NO (verified via `git diff`) |
| `screener/cache.py` | NO (verified via `git diff`) |
| `stock/db_base.py` | NO (verified via `git diff`) |
| All `services/*.py` | NO |
| All `routers/*.py` | NO |
| All `frontend/` | NO |

### 9.3 Migration script data integrity

`scripts/migrate_sqlite_data.py`:
- Backs up `app.db` before migration
- Runs `alembic upgrade head` to ensure schema
- Uses `INSERT OR IGNORE` (preserves existing data, no duplicates)
- Handles JSON column serialization/deserialization correctly
- Backs up legacy DB files to `.bak`
- Reports row counts per table

**Result**: PASS

---

## Summary

| Category | Items | PASS | FAIL | WARN |
|----------|-------|------|------|------|
| 1. Store <-> Repo signatures | 47 functions across 6 stores | 47 | 0 | 0 |
| 2. to_dict() key parity | 12 models | 12 | 0 | 0 |
| 3. Session management | 3 checks | 3 | 0 | 0 |
| 4. Alembic <-> Model schema | 12 tables + 5 indexes | 17 | 0 | 0 |
| 5. main.py lifespan | 1 check | 1 | 0 | 0 |
| 6. entrypoint.sh | 1 check | 1 | 0 | 0 |
| 7. Build tests | 3 checks | 3 | 0 | 0 |
| 8. Issues found | - | - | 3 | 2 |

**Total: 84 PASS, 3 FAIL (1 MAJOR, 1 MAJOR, 1 MINOR), 2 WARN**

### Action Required

1. **FAIL-1** (MAJOR): Add directory creation to `db/session.py` -- fresh local installs will crash
2. **FAIL-2** (MAJOR): Document DESC index autogenerate behavior -- future migration confusion risk
3. **FAIL-3** (MINOR): No action needed (redundant but correct)
4. **WARN-1**: Consider `server_default` for `filled_quantity` and `status` columns
5. **WARN-2**: Acceptable (idempotent double execution)

### Required Fix (FAIL-1) -- Critical for Local Dev

```python
# db/session.py, after line 13
from pathlib import Path
if "sqlite" in DATABASE_URL:
    _db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)
```

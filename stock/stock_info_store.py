"""종목 정보 영속 캐시 (~/stock-watchlist/stock_info.db — SQLite).

Docker 재시작에도 유지되는 종목별 시세/지표/재무/수익률 정보.
cache.db(TTL 캐시, 재시작 시 초기화)와 별도로 운용.
"""

import logging
from datetime import datetime, time
from typing import Optional

from .db_base import KST, connect, now_kst, now_kst_iso, row_to_dict

logger = logging.getLogger(__name__)

_DB = "stock_info.db"

# ── 갱신 정책 (시간 단위) ──────────────────────────────────────────────────────
_TTL = {
    "price":      {"trading": 0.167, "off": 6.0},     # 장중 10분, 장외 6시간
    "metrics":    {"trading": 2.0,   "off": 12.0},     # 장중 2시간, 장외 12시간
    "financials": {"trading": 168.0, "off": 168.0},    # 7일 (장중/장외 동일)
    "returns":    {"trading": 0.5,   "off": 6.0},      # 장중 30분, 장외 6시간
}


def _is_kr_trading_hours() -> bool:
    now = datetime.now(KST)
    return now.weekday() < 5 and time(9, 0) <= now.time() <= time(15, 30)


def _create_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_info (
            code               TEXT NOT NULL,
            market             TEXT NOT NULL DEFAULT 'KR',
            price              REAL,
            change_val         REAL,
            change_pct         REAL,
            mktcap             REAL,
            shares             INTEGER,
            high_52            REAL,
            low_52             REAL,
            price_updated_at   TEXT,
            per                REAL,
            pbr                REAL,
            roe                REAL,
            dividend_yield     REAL,
            dividend_per_share REAL,
            market_type        TEXT,
            sector             TEXT,
            metrics_updated_at TEXT,
            revenue            INTEGER,
            operating_income   INTEGER,
            net_income         INTEGER,
            bsns_year          INTEGER,
            fin_updated_at     TEXT,
            return_3m          REAL,
            return_6m          REAL,
            return_1y          REAL,
            returns_updated_at TEXT,
            PRIMARY KEY (code, market)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_info_price_updated "
        "ON stock_info(price_updated_at)"
    )
    conn.commit()


def _conn():
    return connect(_DB, _create_tables)


# ── staleness 판별 ─────────────────────────────────────────────────────────────

def is_stale(code: str, market: str, field: str) -> bool:
    """해당 영역의 데이터가 갱신이 필요한지 판별."""
    col = f"{field}_updated_at"
    with _conn() as con:
        row = con.execute(
            f"SELECT {col} FROM stock_info WHERE code=? AND market=?",
            (code, market),
        ).fetchone()
    if not row or not row[0]:
        return True

    try:
        updated = datetime.fromisoformat(row[0]).replace(tzinfo=None)
    except (ValueError, TypeError):
        return True

    now = now_kst().replace(tzinfo=None)
    ttl_cfg = _TTL.get(field, {"trading": 1.0, "off": 6.0})
    ttl_h = ttl_cfg["trading"] if _is_kr_trading_hours() else ttl_cfg["off"]

    from datetime import timedelta
    return (now - updated) > timedelta(hours=ttl_h)


# ── 조회 ───────────────────────────────────────────────────────────────────────

def get_stock_info(code: str, market: str = "KR") -> Optional[dict]:
    """종목 정보 조회. 없으면 None."""
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM stock_info WHERE code=? AND market=?",
            (code, market),
        ).fetchone()
    return row_to_dict(row) if row else None


def batch_get(codes_markets: list[tuple]) -> dict:
    """여러 종목 한 번에 조회. {(code, market): dict}."""
    if not codes_markets:
        return {}
    result = {}
    with _conn() as con:
        for code, market in codes_markets:
            row = con.execute(
                "SELECT * FROM stock_info WHERE code=? AND market=?",
                (code, market),
            ).fetchone()
            if row:
                result[(code, market)] = row_to_dict(row)
    return result


# ── 영역별 upsert ──────────────────────────────────────────────────────────────

def _ensure_row(con, code: str, market: str):
    """행이 없으면 빈 행 삽입."""
    con.execute(
        "INSERT OR IGNORE INTO stock_info (code, market) VALUES (?, ?)",
        (code, market),
    )


def upsert_price(code: str, market: str, data: dict) -> None:
    """시세 영역 갱신."""
    try:
        with _conn() as con:
            _ensure_row(con, code, market)
            con.execute("""
                UPDATE stock_info SET
                    price=?, change_val=?, change_pct=?,
                    mktcap=?, shares=?,
                    price_updated_at=?
                WHERE code=? AND market=?
            """, (
                data.get("close") or data.get("price"),
                data.get("change") or data.get("change_val"),
                data.get("change_pct"),
                data.get("mktcap"),
                data.get("shares"),
                now_kst_iso(),
                code, market,
            ))
    except Exception as e:
        logger.debug("stock_info upsert_price error: %s", e)


def upsert_metrics(code: str, market: str, data: dict) -> None:
    """밸류에이션 지표 영역 갱신."""
    try:
        with _conn() as con:
            _ensure_row(con, code, market)
            con.execute("""
                UPDATE stock_info SET
                    per=?, pbr=?, roe=?,
                    dividend_yield=?, dividend_per_share=?,
                    market_type=?, sector=?,
                    high_52=?, low_52=?,
                    metrics_updated_at=?
                WHERE code=? AND market=?
            """, (
                data.get("per"),
                data.get("pbr"),
                data.get("roe"),
                data.get("dividend_yield"),
                data.get("dividend_per_share"),
                data.get("market_type"),
                data.get("sector"),
                data.get("high_52"),
                data.get("low_52"),
                now_kst_iso(),
                code, market,
            ))
    except Exception as e:
        logger.debug("stock_info upsert_metrics error: %s", e)


def upsert_financials(code: str, market: str, data: dict) -> None:
    """재무 영역 갱신."""
    try:
        with _conn() as con:
            _ensure_row(con, code, market)
            con.execute("""
                UPDATE stock_info SET
                    revenue=?, operating_income=?, net_income=?,
                    bsns_year=?,
                    fin_updated_at=?
                WHERE code=? AND market=?
            """, (
                data.get("revenue"),
                data.get("operating_income"),
                data.get("net_income"),
                data.get("bsns_year"),
                now_kst_iso(),
                code, market,
            ))
    except Exception as e:
        logger.debug("stock_info upsert_financials error: %s", e)


def upsert_returns(code: str, market: str, data: dict) -> None:
    """수익률 영역 갱신."""
    try:
        with _conn() as con:
            _ensure_row(con, code, market)
            con.execute("""
                UPDATE stock_info SET
                    return_3m=?, return_6m=?, return_1y=?,
                    returns_updated_at=?
                WHERE code=? AND market=?
            """, (
                data.get("return_3m"),
                data.get("return_6m"),
                data.get("return_1y"),
                now_kst_iso(),
                code, market,
            ))
    except Exception as e:
        logger.debug("stock_info upsert_returns error: %s", e)

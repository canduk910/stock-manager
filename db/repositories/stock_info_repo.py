"""StockInfoRepository — 1:1 mapping to stock/stock_info_store.py functions."""

import logging
from datetime import datetime, time, timedelta
from typing import Optional

from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from db.models.stock_info import StockInfo
from db.utils import KST, now_kst, now_kst_iso

logger = logging.getLogger(__name__)

# ── TTL policy (hours) ──────────────────────────────────────────────────────
_TTL = {
    "price":      {"trading": 0.167, "off": 6.0},
    "metrics":    {"trading": 2.0,   "off": 12.0},
    "financials": {"trading": 168.0, "off": 168.0},
    "returns":    {"trading": 0.5,   "off": 6.0},
}


def _is_kr_trading_hours() -> bool:
    now = datetime.now(KST)
    return now.weekday() < 5 and time(9, 0) <= now.time() <= time(15, 30)


class StockInfoRepository:
    def __init__(self, db: Session):
        self.db = db

    def is_stale(self, code: str, market: str, field: str) -> bool:
        """Check if the given data region needs refresh."""
        col_name = f"{field}_updated_at"
        row = (
            self.db.query(StockInfo)
            .filter_by(code=code, market=market)
            .first()
        )
        if not row:
            return True

        updated_str = getattr(row, col_name, None)
        if not updated_str:
            return True

        try:
            updated = datetime.fromisoformat(updated_str).replace(tzinfo=None)
        except (ValueError, TypeError):
            return True

        now = now_kst().replace(tzinfo=None)
        ttl_cfg = _TTL.get(field, {"trading": 1.0, "off": 6.0})
        ttl_h = ttl_cfg["trading"] if _is_kr_trading_hours() else ttl_cfg["off"]
        return (now - updated) > timedelta(hours=ttl_h)

    def get_stock_info(self, code: str, market: str = "KR") -> Optional[dict]:
        row = (
            self.db.query(StockInfo)
            .filter_by(code=code, market=market)
            .first()
        )
        return row.to_dict() if row else None

    def batch_get(self, codes_markets: list[tuple]) -> dict:
        if not codes_markets:
            return {}
        conditions = [
            and_(StockInfo.code == code, StockInfo.market == market)
            for code, market in codes_markets
        ]
        rows = self.db.query(StockInfo).filter(or_(*conditions)).all()
        return {(r.code, r.market): r.to_dict() for r in rows}

    def _ensure_row(self, code: str, market: str) -> StockInfo:
        """Get or create a StockInfo row (check-then-insert, F2 pattern)."""
        row = (
            self.db.query(StockInfo)
            .filter_by(code=code, market=market)
            .first()
        )
        if not row:
            row = StockInfo(code=code, market=market)
            self.db.add(row)
            self.db.flush()
        return row

    def upsert_price(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.price = data.get("close") or data.get("price")
            row.change_val = data.get("change") or data.get("change_val")
            row.change_pct = data.get("change_pct")
            row.mktcap = data.get("mktcap")
            row.shares = data.get("shares")
            row.price_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_price error: %s", e)

    def upsert_metrics(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.per = data.get("per")
            row.pbr = data.get("pbr")
            row.roe = data.get("roe")
            row.dividend_yield = data.get("dividend_yield")
            row.dividend_per_share = data.get("dividend_per_share")
            row.market_type = data.get("market_type")
            row.sector = data.get("sector")
            row.high_52 = data.get("high_52")
            row.low_52 = data.get("low_52")
            row.metrics_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_metrics error: %s", e)

    def upsert_financials(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.revenue = data.get("revenue")
            row.operating_income = data.get("operating_income")
            row.net_income = data.get("net_income")
            row.bsns_year = data.get("bsns_year")
            row.fin_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_financials error: %s", e)

    def upsert_returns(self, code: str, market: str, data: dict) -> None:
        try:
            row = self._ensure_row(code, market)
            row.return_3m = data.get("return_3m")
            row.return_6m = data.get("return_6m")
            row.return_1y = data.get("return_1y")
            row.returns_updated_at = now_kst_iso()
        except Exception as e:
            logger.warning("stock_info upsert_returns error: %s", e)

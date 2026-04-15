"""AdvisoryRepository — 1:1 mapping to stock/advisory_store.py functions."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.advisory import (
    AdvisoryCache,
    AdvisoryReport,
    AdvisoryStock,
    PortfolioReport,
)
from db.utils import now_kst_iso


class AdvisoryRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Advisory Stocks CRUD ────────────────────────────────────

    def add_stock(self, code: str, market: str, name: str, memo: str = "") -> bool:
        code_u, market_u = code.upper(), market.upper()
        existing = (
            self.db.query(AdvisoryStock)
            .filter_by(code=code_u, market=market_u)
            .first()
        )
        if existing:
            return False
        self.db.add(AdvisoryStock(
            code=code_u,
            market=market_u,
            name=name,
            added_date=now_kst_iso(),
            memo=memo,
        ))
        return True

    def remove_stock(self, code: str, market: str) -> bool:
        count = (
            self.db.query(AdvisoryStock)
            .filter_by(code=code.upper(), market=market.upper())
            .delete()
        )
        return count > 0

    def all_stocks(self) -> list[dict]:
        rows = (
            self.db.query(AdvisoryStock)
            .order_by(AdvisoryStock.added_date.desc())
            .all()
        )
        return [r.to_dict() for r in rows]

    def get_stock(self, code: str, market: str) -> Optional[dict]:
        row = (
            self.db.query(AdvisoryStock)
            .filter_by(code=code.upper(), market=market.upper())
            .first()
        )
        return row.to_dict() if row else None

    # ── Cache CRUD ──────────────────────────────────────────────

    def save_cache(self, code: str, market: str, fundamental: dict, technical: dict) -> None:
        code_u, market_u = code.upper(), market.upper()
        row = (
            self.db.query(AdvisoryCache)
            .filter_by(code=code_u, market=market_u)
            .first()
        )
        if not row:
            row = AdvisoryCache(code=code_u, market=market_u)
            self.db.add(row)
        row.updated_at = now_kst_iso()
        row.fundamental = fundamental
        row.technical = technical

    def get_cache(self, code: str, market: str) -> Optional[dict]:
        row = (
            self.db.query(AdvisoryCache)
            .filter_by(code=code.upper(), market=market.upper())
            .first()
        )
        return row.to_dict() if row else None

    # ── Report CRUD ─────────────────────────────────────────────

    def save_report(self, code: str, market: str, model: str, report: dict) -> int:
        r = AdvisoryReport(
            code=code.upper(),
            market=market.upper(),
            generated_at=now_kst_iso(),
            model=model,
            report=report,
        )
        self.db.add(r)
        self.db.flush()
        return r.id

    def get_report_history(self, code: str, market: str, limit: int = 20) -> list[dict]:
        rows = (
            self.db.query(AdvisoryReport)
            .filter_by(code=code.upper(), market=market.upper())
            .order_by(AdvisoryReport.id.desc())
            .limit(limit)
            .all()
        )
        return [r.to_summary_dict() for r in rows]

    def get_report_by_id(self, report_id: int) -> Optional[dict]:
        row = self.db.query(AdvisoryReport).filter_by(id=report_id).first()
        return row.to_dict() if row else None

    def get_latest_report(self, code: str, market: str) -> Optional[dict]:
        row = (
            self.db.query(AdvisoryReport)
            .filter_by(code=code.upper(), market=market.upper())
            .order_by(AdvisoryReport.id.desc())
            .first()
        )
        return row.to_dict() if row else None

    # ── Portfolio Report CRUD ───────────────────────────────────

    def save_portfolio_report(self, model: str, report: dict) -> int:
        r = PortfolioReport(
            generated_at=now_kst_iso(),
            model=model,
            report=report,
        )
        self.db.add(r)
        self.db.flush()
        return r.id

    def get_portfolio_report_history(self, limit: int = 20) -> list[dict]:
        rows = (
            self.db.query(PortfolioReport)
            .order_by(PortfolioReport.id.desc())
            .limit(limit)
            .all()
        )
        return [r.to_summary_dict() for r in rows]

    def get_portfolio_report_by_id(self, report_id: int) -> Optional[dict]:
        row = self.db.query(PortfolioReport).filter_by(id=report_id).first()
        return row.to_dict() if row else None

    def get_latest_portfolio_report(self) -> Optional[dict]:
        row = (
            self.db.query(PortfolioReport)
            .order_by(PortfolioReport.id.desc())
            .first()
        )
        return row.to_dict() if row else None

"""ReportRepository — CRUD for RecommendationHistory, MacroRegimeHistory, DailyReport."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.report import DailyReport, MacroRegimeHistory, RecommendationHistory
from stock.db_base import now_kst_iso


class ReportRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── RecommendationHistory ─────────────────────────────────

    def save_recommendation(self, **kwargs) -> int:
        rec = RecommendationHistory(
            created_at=now_kst_iso(),
            status="recommended",
            **kwargs,
        )
        self.db.add(rec)
        self.db.flush()
        return rec.id

    def save_recommendations_batch(self, items: list[dict]) -> list[int]:
        ids = []
        ts = now_kst_iso()
        for item in items:
            rec = RecommendationHistory(
                created_at=ts,
                status="recommended",
                **item,
            )
            self.db.add(rec)
            self.db.flush()
            ids.append(rec.id)
        return ids

    def update_recommendation_status(
        self, rec_id: int, status: str, **kwargs
    ) -> bool:
        rec = self.db.query(RecommendationHistory).filter_by(id=rec_id).first()
        if not rec:
            return False
        rec.status = status
        if status == "approved":
            rec.approved_at = kwargs.get("approved_at", now_kst_iso())
        if status == "ordered":
            rec.order_id = kwargs.get("order_id")
        if status == "closed":
            rec.closed_at = kwargs.get("closed_at", now_kst_iso())
            rec.closed_price = kwargs.get("closed_price")
            if rec.entry_price and rec.closed_price:
                rec.realized_pnl_pct = round(
                    (rec.closed_price - rec.entry_price) / rec.entry_price * 100, 2
                )
        return True

    def get_recommendation(self, rec_id: int) -> Optional[dict]:
        rec = self.db.query(RecommendationHistory).filter_by(id=rec_id).first()
        return rec.to_dict() if rec else None

    def list_recommendations(
        self,
        market: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        q = self.db.query(RecommendationHistory)
        if market:
            q = q.filter(RecommendationHistory.market == market.upper())
        if status:
            q = q.filter(RecommendationHistory.status == status)
        rows = (
            q.order_by(RecommendationHistory.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in rows]

    def list_recommendations_by_date(self, date: str, market: Optional[str] = None) -> list[dict]:
        q = self.db.query(RecommendationHistory).filter(
            RecommendationHistory.created_at.like(f"{date}%")
        )
        if market:
            q = q.filter(RecommendationHistory.market == market.upper())
        rows = q.order_by(RecommendationHistory.id.desc()).all()
        return [r.to_dict() for r in rows]

    def count_recommendations(
        self, market: Optional[str] = None, status: Optional[str] = None
    ) -> int:
        q = self.db.query(RecommendationHistory)
        if market:
            q = q.filter(RecommendationHistory.market == market.upper())
        if status:
            q = q.filter(RecommendationHistory.status == status)
        return q.count()

    def get_performance_stats(self, market: Optional[str] = None) -> dict:
        q = self.db.query(RecommendationHistory).filter(
            RecommendationHistory.status == "closed"
        )
        if market:
            q = q.filter(RecommendationHistory.market == market.upper())
        closed = q.all()
        if not closed:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "avg_pnl": 0}
        wins = [r for r in closed if (r.realized_pnl_pct or 0) > 0]
        losses = [r for r in closed if (r.realized_pnl_pct or 0) <= 0]
        avg_pnl = sum(r.realized_pnl_pct or 0 for r in closed) / len(closed)
        return {
            "total": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(closed) * 100, 1),
            "avg_pnl": round(avg_pnl, 2),
        }

    # ── MacroRegimeHistory ────────────────────────────────────

    def save_regime(self, date: str, regime: str, **kwargs) -> int:
        existing = self.db.query(MacroRegimeHistory).filter_by(date=date).first()
        if existing:
            existing.regime = regime
            for k, v in kwargs.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            self.db.flush()
            return existing.id
        row = MacroRegimeHistory(
            date=date,
            regime=regime,
            created_at=now_kst_iso(),
            **kwargs,
        )
        self.db.add(row)
        self.db.flush()
        return row.id

    def get_regime(self, date: str) -> Optional[dict]:
        row = self.db.query(MacroRegimeHistory).filter_by(date=date).first()
        return row.to_dict() if row else None

    def get_latest_regime(self) -> Optional[dict]:
        row = (
            self.db.query(MacroRegimeHistory)
            .order_by(MacroRegimeHistory.date.desc())
            .first()
        )
        return row.to_dict() if row else None

    def list_regimes(self, limit: int = 90) -> list[dict]:
        rows = (
            self.db.query(MacroRegimeHistory)
            .order_by(MacroRegimeHistory.date.desc())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in rows]

    # ── DailyReport ───────────────────────────────────────────

    def save_daily_report(
        self,
        date: str,
        market: str,
        report_markdown: str,
        report_json: Optional[dict] = None,
        regime: Optional[str] = None,
        candidates_count: int = 0,
        recommended_count: int = 0,
    ) -> int:
        row = DailyReport(
            date=date,
            market=market.upper(),
            regime=regime,
            candidates_count=candidates_count,
            recommended_count=recommended_count,
            report_markdown=report_markdown,
            report_json=report_json,
            created_at=now_kst_iso(),
        )
        self.db.add(row)
        self.db.flush()
        return row.id

    def mark_telegram_sent(self, report_id: int) -> bool:
        row = self.db.query(DailyReport).filter_by(id=report_id).first()
        if not row:
            return False
        row.telegram_sent = 1
        return True

    def get_daily_report(self, report_id: int) -> Optional[dict]:
        row = self.db.query(DailyReport).filter_by(id=report_id).first()
        return row.to_dict() if row else None

    def get_daily_report_by_date(self, date: str, market: str) -> Optional[dict]:
        row = (
            self.db.query(DailyReport)
            .filter_by(date=date, market=market.upper())
            .first()
        )
        return row.to_dict() if row else None

    def list_daily_reports(
        self,
        market: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict]:
        q = self.db.query(DailyReport)
        if market:
            q = q.filter(DailyReport.market == market.upper())
        rows = (
            q.order_by(DailyReport.date.desc(), DailyReport.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [r.to_summary_dict() for r in rows]

    def count_daily_reports(self, market: Optional[str] = None) -> int:
        q = self.db.query(DailyReport)
        if market:
            q = q.filter(DailyReport.market == market.upper())
        return q.count()

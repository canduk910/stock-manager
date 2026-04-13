"""Report models: RecommendationHistory, MacroRegimeHistory, DailyReport."""

from sqlalchemy import Column, Float, Index, Integer, String, Text
from sqlalchemy.types import JSON

from db.base import Base


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String, nullable=False)
    market = Column(String, nullable=False)  # KR / US
    regime = Column(String, nullable=False)
    code = Column(String, nullable=False)
    name = Column(String, nullable=False)
    graham_number = Column(Float)
    entry_price = Column(Float, nullable=False)
    safety_grade = Column(String)  # A / B+ / B / C / D
    discount_rate = Column(Float)
    recommended_qty = Column(Integer, nullable=False)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_reward = Column(Float)
    reasoning = Column(Text, default="")
    # 실행 추적
    order_id = Column(Integer)  # FK → orders (논리적 참조)
    status = Column(String, nullable=False, default="recommended")
    approved_at = Column(String)
    # 성과 추적
    closed_at = Column(String)
    closed_price = Column(Float)
    realized_pnl_pct = Column(Float)

    __table_args__ = (
        Index("idx_rec_hist_market_date", "market", "created_at"),
        Index("idx_rec_hist_code", "code", "market"),
        Index("idx_rec_hist_status", "status"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "market": self.market,
            "regime": self.regime,
            "code": self.code,
            "name": self.name,
            "graham_number": self.graham_number,
            "entry_price": self.entry_price,
            "safety_grade": self.safety_grade,
            "discount_rate": self.discount_rate,
            "recommended_qty": self.recommended_qty,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "reasoning": self.reasoning,
            "order_id": self.order_id,
            "status": self.status,
            "approved_at": self.approved_at,
            "closed_at": self.closed_at,
            "closed_price": self.closed_price,
            "realized_pnl_pct": self.realized_pnl_pct,
        }

    def to_summary_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "market": self.market,
            "code": self.code,
            "name": self.name,
            "safety_grade": self.safety_grade,
            "entry_price": self.entry_price,
            "status": self.status,
            "realized_pnl_pct": self.realized_pnl_pct,
        }


class MacroRegimeHistory(Base):
    __tablename__ = "macro_regime_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False, unique=True)  # YYYY-MM-DD
    regime = Column(String, nullable=False)
    buffett_ratio = Column(Float)
    vix = Column(Float)
    fear_greed_score = Column(Float)
    kospi = Column(Float)
    sp500 = Column(Float)
    notes = Column(Text, default="")
    created_at = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_macro_regime_date", "date"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "regime": self.regime,
            "buffett_ratio": self.buffett_ratio,
            "vix": self.vix,
            "fear_greed_score": self.fear_greed_score,
            "kospi": self.kospi,
            "sp500": self.sp500,
            "notes": self.notes,
            "created_at": self.created_at,
        }


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    market = Column(String, nullable=False)  # KR / US / ALL
    regime = Column(String)
    candidates_count = Column(Integer, default=0)
    recommended_count = Column(Integer, default=0)
    report_markdown = Column(Text, nullable=False)
    report_json = Column(JSON)
    telegram_sent = Column(Integer, default=0)  # SQLite: 0/1 boolean
    created_at = Column(String, nullable=False)

    __table_args__ = (
        Index("idx_daily_reports_date_market", "date", "market"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "market": self.market,
            "regime": self.regime,
            "candidates_count": self.candidates_count,
            "recommended_count": self.recommended_count,
            "report_markdown": self.report_markdown,
            "report_json": self.report_json,
            "telegram_sent": bool(self.telegram_sent),
            "created_at": self.created_at,
        }

    def to_summary_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date,
            "market": self.market,
            "regime": self.regime,
            "candidates_count": self.candidates_count,
            "recommended_count": self.recommended_count,
            "telegram_sent": bool(self.telegram_sent),
            "created_at": self.created_at,
        }

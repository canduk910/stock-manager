"""Advisory models: AdvisoryStock, AdvisoryCache, AdvisoryReport, PortfolioReport."""

from sqlalchemy import Column, Index, Integer, String, Text
from sqlalchemy.types import JSON

from db.base import Base


class AdvisoryStock(Base):
    __tablename__ = "advisory_stocks"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    name = Column(String, nullable=False)
    added_date = Column(String, nullable=False)
    memo = Column(Text, nullable=False, default="")

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "name": self.name,
            "added_date": self.added_date,
            "memo": self.memo,
        }


class AdvisoryCache(Base):
    __tablename__ = "advisory_cache"

    code = Column(String, primary_key=True)
    market = Column(String, primary_key=True, default="KR")
    updated_at = Column(String, nullable=False)
    fundamental = Column(JSON)
    technical = Column(JSON)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "updated_at": self.updated_at,
            "fundamental": self.fundamental or {},
            "technical": self.technical or {},
        }


class AdvisoryReport(Base):
    __tablename__ = "advisory_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False)
    market = Column(String, nullable=False, default="KR")
    generated_at = Column(String, nullable=False)
    model = Column(String, nullable=False)
    report = Column(JSON, nullable=False)

    __table_args__ = (
        Index("idx_advisory_reports_code_market", "code", "market", "generated_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "market": self.market,
            "generated_at": self.generated_at,
            "model": self.model,
            "report": self.report or {},
        }

    def to_summary_dict(self) -> dict:
        """Report history (without body)."""
        return {
            "id": self.id,
            "code": self.code,
            "market": self.market,
            "generated_at": self.generated_at,
            "model": self.model,
        }


class PortfolioReport(Base):
    __tablename__ = "portfolio_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(String, nullable=False)
    model = Column(String, nullable=False)
    report = Column(JSON, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "generated_at": self.generated_at,
            "model": self.model,
            "report": self.report or {},
        }

    def to_summary_dict(self) -> dict:
        """Report history (without body)."""
        return {
            "id": self.id,
            "generated_at": self.generated_at,
            "model": self.model,
        }

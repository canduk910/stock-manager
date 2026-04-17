"""Advisory models: AdvisoryStock, AdvisoryCache, AdvisoryReport, PortfolioReport."""

from sqlalchemy import Boolean, Column, Float, Index, Integer, String, Text
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
    strategy_signals = Column(JSON, nullable=True)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "market": self.market,
            "updated_at": self.updated_at,
            "fundamental": self.fundamental or {},
            "technical": self.technical or {},
            "strategy_signals": self.strategy_signals,
        }


class AdvisoryReport(Base):
    __tablename__ = "advisory_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False)
    market = Column(String, nullable=False, default="KR")
    generated_at = Column(String, nullable=False)
    model = Column(String, nullable=False)
    report = Column(JSON, nullable=False)
    # Phase 3 신규 컬럼 (모두 nullable, 기존 데이터 영향 없음)
    grade = Column(String, nullable=True)               # A/B+/B/C/D
    grade_score = Column(Integer, nullable=True)         # 0~28
    composite_score = Column(Float, nullable=True)       # 0~100
    regime_alignment = Column(Float, nullable=True)      # 0~100
    schema_version = Column(String, nullable=True, default="v1")  # v1/v2
    value_trap_warning = Column(Boolean, nullable=True, default=False)

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
            "grade": self.grade,
            "grade_score": self.grade_score,
            "composite_score": self.composite_score,
            "regime_alignment": self.regime_alignment,
            "schema_version": self.schema_version or "v1",
            "value_trap_warning": self.value_trap_warning or False,
        }

    def to_summary_dict(self) -> dict:
        """Report history (without body)."""
        return {
            "id": self.id,
            "code": self.code,
            "market": self.market,
            "generated_at": self.generated_at,
            "model": self.model,
            "grade": self.grade,
            "grade_score": self.grade_score,
            "schema_version": self.schema_version or "v1",
        }


class PortfolioReport(Base):
    __tablename__ = "portfolio_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(String, nullable=False)
    model = Column(String, nullable=False)
    report = Column(JSON, nullable=False)
    # Phase 3 신규 컬럼
    weighted_grade_avg = Column(Float, nullable=True)
    regime = Column(String, nullable=True)
    schema_version = Column(String, nullable=True, default="v1")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "generated_at": self.generated_at,
            "model": self.model,
            "report": self.report or {},
            "weighted_grade_avg": self.weighted_grade_avg,
            "regime": self.regime,
            "schema_version": self.schema_version or "v1",
        }

    def to_summary_dict(self) -> dict:
        """Report history (without body)."""
        return {
            "id": self.id,
            "generated_at": self.generated_at,
            "model": self.model,
            "weighted_grade_avg": self.weighted_grade_avg,
            "regime": self.regime,
        }

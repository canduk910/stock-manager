"""Backtest models: BacktestJob, Strategy."""

from sqlalchemy import Column, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.types import JSON

from db.base import Base


class BacktestJob(Base):
    __tablename__ = "backtest_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1)
    job_id = Column(String, unique=True, nullable=False)
    strategy_name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    market = Column(String, nullable=False, default="KR")
    strategy_type = Column(String, nullable=False)  # preset/custom
    status = Column(String, nullable=False, default="submitted")
    submitted_at = Column(String, nullable=False)
    completed_at = Column(String, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    cagr = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    result_json = Column(JSON, nullable=True)
    params_json = Column(JSON, nullable=True)
    strategy_display_name = Column(String, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "strategy_name": self.strategy_name,
            "strategy_display_name": self.strategy_display_name,
            "symbol": self.symbol,
            "market": self.market,
            "strategy_type": self.strategy_type,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "completed_at": self.completed_at,
            "total_return_pct": self.total_return_pct,
            "cagr": self.cagr,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "result_json": self.result_json,
            "params_json": self.params_json,
        }


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, default=1)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(String, nullable=False)  # preset/custom
    yaml_content = Column(Text, nullable=True)
    builder_state_json = Column(JSON, nullable=True)
    created_at = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_strategy_user_name"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "strategy_type": self.strategy_type,
            "yaml_content": self.yaml_content,
            "builder_state_json": self.builder_state_json,
            "created_at": self.created_at,
        }

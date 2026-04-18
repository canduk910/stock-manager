"""BacktestRepository — BacktestJob + Strategy CRUD."""

from typing import Optional

from sqlalchemy.orm import Session

from db.models.backtest import BacktestJob, Strategy
from db.utils import now_kst_iso


class BacktestRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── BacktestJob CRUD ──────────────────────────────────────

    def create_job(
        self,
        job_id: str,
        strategy_name: str,
        symbol: str,
        market: str,
        strategy_type: str,
        submitted_at: str,
    ) -> dict:
        job = BacktestJob(
            job_id=job_id,
            strategy_name=strategy_name,
            symbol=symbol.upper(),
            market=market.upper(),
            strategy_type=strategy_type,
            status="submitted",
            submitted_at=submitted_at,
        )
        self.db.add(job)
        self.db.flush()
        return job.to_dict()

    def update_job_result(
        self,
        job_id: str,
        metrics: dict,
        result_json: dict,
        completed_at: str,
    ) -> bool:
        job = self.db.query(BacktestJob).filter_by(job_id=job_id).first()
        if not job:
            return False
        job.status = "completed"
        job.completed_at = completed_at
        job.total_return_pct = metrics.get("total_return_pct")
        job.cagr = metrics.get("cagr")
        job.sharpe_ratio = metrics.get("sharpe_ratio")
        job.sortino_ratio = metrics.get("sortino_ratio")
        job.max_drawdown = metrics.get("max_drawdown")
        job.win_rate = metrics.get("win_rate")
        job.profit_factor = metrics.get("profit_factor")
        job.total_trades = metrics.get("total_trades")
        job.result_json = result_json
        return True

    def update_job_status(self, job_id: str, status: str) -> bool:
        job = self.db.query(BacktestJob).filter_by(job_id=job_id).first()
        if not job:
            return False
        job.status = status
        if status in ("completed", "failed"):
            job.completed_at = now_kst_iso()
        return True

    def get_job(self, job_id: str) -> Optional[dict]:
        job = self.db.query(BacktestJob).filter_by(job_id=job_id).first()
        return job.to_dict() if job else None

    def get_latest_metrics(self, symbol: str, market: str) -> Optional[dict]:
        """해당 종목의 가장 최근 completed job 메트릭."""
        job = (
            self.db.query(BacktestJob)
            .filter_by(symbol=symbol.upper(), market=market.upper(), status="completed")
            .order_by(BacktestJob.id.desc())
            .first()
        )
        if not job:
            return None
        return {
            "job_id": job.job_id,
            "strategy_name": job.strategy_name,
            "total_return_pct": job.total_return_pct,
            "cagr": job.cagr,
            "sharpe_ratio": job.sharpe_ratio,
            "sortino_ratio": job.sortino_ratio,
            "max_drawdown": job.max_drawdown,
            "win_rate": job.win_rate,
            "profit_factor": job.profit_factor,
            "total_trades": job.total_trades,
            "completed_at": job.completed_at,
        }

    def list_jobs(
        self,
        symbol: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        q = self.db.query(BacktestJob)
        if symbol:
            q = q.filter_by(symbol=symbol.upper())
        if market:
            q = q.filter_by(market=market.upper())
        rows = q.order_by(BacktestJob.id.desc()).limit(limit).all()
        return [r.to_dict() for r in rows]

    def delete_job(self, job_id: str) -> bool:
        job = self.db.query(BacktestJob).filter_by(job_id=job_id).first()
        if not job:
            return False
        self.db.delete(job)
        return True

    # ── Strategy CRUD ─────────────────────────────────────────

    def save_strategy(
        self,
        name: str,
        strategy_type: str,
        description: Optional[str] = None,
        yaml_content: Optional[str] = None,
    ) -> dict:
        existing = self.db.query(Strategy).filter_by(name=name).first()
        if existing:
            existing.description = description
            existing.strategy_type = strategy_type
            existing.yaml_content = yaml_content
            self.db.flush()
            return existing.to_dict()
        s = Strategy(
            name=name,
            description=description,
            strategy_type=strategy_type,
            yaml_content=yaml_content,
            created_at=now_kst_iso(),
        )
        self.db.add(s)
        self.db.flush()
        return s.to_dict()

    def list_strategies(self, strategy_type: Optional[str] = None) -> list[dict]:
        q = self.db.query(Strategy)
        if strategy_type:
            q = q.filter_by(strategy_type=strategy_type)
        rows = q.order_by(Strategy.id.desc()).all()
        return [r.to_dict() for r in rows]

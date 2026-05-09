"""BacktestRepository — BacktestJob + Strategy CRUD."""

import logging
from typing import Optional

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from db.models.backtest import BacktestJob, Strategy
from db.utils import now_kst_iso

logger = logging.getLogger(__name__)


def _is_symbols_column_missing(err: Exception) -> bool:
    """SQL 에러 메시지에서 `symbols` 컬럼 부재 패턴 식별.

    PostgreSQL: 'column "symbols" of relation "backtest_jobs" does not exist'
    SQLite:     'no such column: backtest_jobs.symbols'
    MySQL:      "Unknown column 'symbols'"
    """
    msg = str(err).lower()
    return "symbols" in msg and (
        "does not exist" in msg
        or "no such column" in msg
        or "unknown column" in msg
    )


def _is_mcp_job_id_column_missing(err: Exception) -> bool:
    """SQL 에러 메시지에서 `mcp_job_id` 컬럼 부재 패턴 식별 (alembic 미적용 환경)."""
    msg = str(err).lower()
    return "mcp_job_id" in msg and (
        "does not exist" in msg
        or "no such column" in msg
        or "unknown column" in msg
    )


class BacktestRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── BacktestJob CRUD ──────────────────────────────────────

    def create_job(
        self,
        user_id: int,
        job_id: str,
        strategy_name: str,
        symbol: str,
        market: str,
        strategy_type: str,
        submitted_at: str,
        params: dict | None = None,
        strategy_display_name: str | None = None,
        symbols: list[str] | None = None,
    ) -> dict:
        symbols_payload = [s.upper() for s in symbols] if symbols else None

        def _build(include_symbols: bool) -> BacktestJob:
            return BacktestJob(
                user_id=user_id,
                job_id=job_id,
                strategy_name=strategy_name,
                strategy_display_name=strategy_display_name,
                symbol=symbol.upper(),
                # graceful 모드: symbols 키 자체를 제외 (alembic 미적용 호환)
                symbols=symbols_payload if include_symbols else None,
                market=market.upper(),
                strategy_type=strategy_type,
                status="submitted",
                submitted_at=submitted_at,
                params_json=params,
            )

        job = _build(include_symbols=True)
        self.db.add(job)
        try:
            self.db.flush()
        except (OperationalError, ProgrammingError) as e:
            # alembic 미적용 환경: `symbols` 컬럼 부재 시 그것만 제외하고 재시도.
            # 이외 SQL 오류는 그대로 raise → 상위에서 ServiceError 변환.
            if not _is_symbols_column_missing(e):
                raise
            logger.error(
                "[REQ-FIX-01] backtest_jobs.symbols 컬럼 부재 (alembic 미적용 추정) "
                "— symbols 제외하고 재시도. err=%s",
                e,
            )
            self.db.rollback()
            job = _build(include_symbols=False)
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

    def set_mcp_job_id(self, job_id: str, mcp_job_id: str) -> bool:
        """fire-and-poll: MCP 측 job_id를 DB 행에 기록.

        alembic 미적용 환경에서 mcp_job_id 컬럼 부재 시 silent skip
        (graceful degrade — 폴링은 동작 안 하지만 동기 응답으로 폴백 가능).
        """
        try:
            job = self.db.query(BacktestJob).filter_by(job_id=job_id).first()
            if not job:
                return False
            job.mcp_job_id = mcp_job_id
            self.db.flush()
            return True
        except (OperationalError, ProgrammingError) as e:
            if not _is_mcp_job_id_column_missing(e):
                raise
            logger.error(
                "backtest_jobs.mcp_job_id 컬럼 부재 (alembic 미적용 추정) — "
                "fire-and-poll 비활성화 (동기 응답 폴백). err=%s",
                e,
            )
            self.db.rollback()
            return False

    def update_job_failed(self, job_id: str, error_message: str) -> bool:
        """실패 시 status="failed" + result_json.error_message 저장."""
        job = self.db.query(BacktestJob).filter_by(job_id=job_id).first()
        if not job:
            return False
        job.status = "failed"
        job.completed_at = now_kst_iso()
        existing = job.result_json if isinstance(job.result_json, dict) else {}
        existing = dict(existing)
        existing["error_message"] = error_message
        job.result_json = existing
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
        user_id: int,
        symbol: Optional[str] = None,
        market: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        q = self.db.query(BacktestJob).filter_by(user_id=user_id)
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
        user_id: int,
        name: str,
        strategy_type: str,
        description: Optional[str] = None,
        yaml_content: Optional[str] = None,
        builder_state_json: Optional[dict] = None,
    ) -> dict:
        existing = self.db.query(Strategy).filter_by(user_id=user_id, name=name).first()
        if existing:
            existing.description = description
            existing.strategy_type = strategy_type
            existing.yaml_content = yaml_content
            existing.builder_state_json = builder_state_json
            self.db.flush()
            return existing.to_dict()
        s = Strategy(
            user_id=user_id,
            name=name,
            description=description,
            strategy_type=strategy_type,
            yaml_content=yaml_content,
            builder_state_json=builder_state_json,
            created_at=now_kst_iso(),
        )
        self.db.add(s)
        self.db.flush()
        return s.to_dict()

    def get_strategy(self, user_id: int, name: str) -> Optional[dict]:
        s = self.db.query(Strategy).filter_by(user_id=user_id, name=name).first()
        return s.to_dict() if s else None

    def delete_strategy(self, user_id: int, name: str) -> bool:
        s = self.db.query(Strategy).filter_by(user_id=user_id, name=name).first()
        if not s:
            return False
        self.db.delete(s)
        return True

    def list_strategies(self, user_id: int, strategy_type: Optional[str] = None) -> list[dict]:
        q = self.db.query(Strategy).filter_by(user_id=user_id)
        if strategy_type:
            q = q.filter_by(strategy_type=strategy_type)
        rows = q.order_by(Strategy.id.desc()).all()
        return [r.to_dict() for r in rows]

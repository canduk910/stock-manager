"""백테스트 작업 + 전략 CRUD — SQLAlchemy ORM adapter.

기존 store 패턴 따름. 내부는 BacktestRepository에 위임.
"""

from typing import Optional

from db.repositories.backtest_repo import BacktestRepository
from db.session import get_session


# ── BacktestJob CRUD ─────────────────────────────────────────────────────────

def save_backtest_job(
    job_id: str,
    strategy_name: str,
    symbol: str,
    market: str,
    strategy_type: str,
    submitted_at: str,
    params: dict | None = None,
    strategy_display_name: str | None = None,
) -> dict:
    """백테스트 작업 저장."""
    with get_session() as db:
        return BacktestRepository(db).create_job(
            job_id, strategy_name, symbol, market, strategy_type, submitted_at,
            params=params, strategy_display_name=strategy_display_name,
        )


def save_backtest_result(
    job_id: str,
    metrics: dict,
    result_json: dict,
    completed_at: str,
) -> bool:
    """백테스트 결과 저장."""
    with get_session() as db:
        return BacktestRepository(db).update_job_result(
            job_id, metrics, result_json, completed_at,
        )


def update_job_status(job_id: str, status: str) -> bool:
    """작업 상태 변경."""
    with get_session() as db:
        return BacktestRepository(db).update_job_status(job_id, status)


def get_job(job_id: str) -> Optional[dict]:
    """작업 조회."""
    with get_session() as db:
        return BacktestRepository(db).get_job(job_id)


def get_latest_backtest_metrics(symbol: str, market: str) -> Optional[dict]:
    """해당 종목의 가장 최근 completed job 메트릭."""
    with get_session() as db:
        return BacktestRepository(db).get_latest_metrics(symbol, market)


def delete_job(job_id: str) -> bool:
    """백테스트 작업 삭제."""
    with get_session() as db:
        return BacktestRepository(db).delete_job(job_id)


def get_job_history(
    symbol: Optional[str] = None,
    market: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """작업 이력 조회."""
    with get_session() as db:
        return BacktestRepository(db).list_jobs(symbol, market, limit)


# ── Strategy CRUD ─────────────────────────────────────────────────────────


def save_strategy(
    name: str,
    strategy_type: str,
    description: Optional[str] = None,
    yaml_content: Optional[str] = None,
    builder_state: Optional[dict] = None,
) -> dict:
    """전략 저장."""
    with get_session() as db:
        return BacktestRepository(db).save_strategy(
            name, strategy_type, description, yaml_content, builder_state,
        )


def list_strategies(strategy_type: Optional[str] = None) -> list[dict]:
    """전략 목록 조회."""
    with get_session() as db:
        return BacktestRepository(db).list_strategies(strategy_type)


def get_strategy(name: str) -> Optional[dict]:
    """전략 조회."""
    with get_session() as db:
        return BacktestRepository(db).get_strategy(name)


def delete_strategy(name: str) -> bool:
    """전략 삭제."""
    with get_session() as db:
        return BacktestRepository(db).delete_strategy(name)

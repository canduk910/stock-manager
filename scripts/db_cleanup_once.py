#!/usr/bin/env python3
"""DB retention 백로그 1회 정리 + VACUUM (2026-07-17 신규).

배포 직후 기존에 무제한 누적된 append-only 로그/이력 테이블을 1회 대량 정리하고
공간을 회수한다. 매일 03:00 `_run_db_retention_cleanup_job()`이 이후 성장을 억제.

실행:
    python -m scripts.db_cleanup_once

동작 순서:
1. before 실측: PostgreSQL이면 `pg_total_relation_size` + row count, SQLite면 row count만.
2. `services.scheduler_service._run_db_retention_cleanup_job()` 재사용 호출 (Part B와 동일 로직).
3. VACUUM: PostgreSQL이면 autocommit 연결에서 `VACUUM (VERBOSE, ANALYZE)` 전체 +
   최대 누적 테이블(page_views)은 `VACUUM FULL page_views` 별도. SQLite면 `VACUUM;`.
4. after 실측 + 절감량 로깅.

주의: 사용자 실 데이터 파일에 대해 실행 시 대량 DELETE + VACUUM FULL(page_views, 짧은
exclusive lock)이 발생한다. 운영 실행은 트래픽 최저 구간에서 수행할 것.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_cleanup_once")

# 정리 대상 9개 테이블 (요건서 Part A/B 범위와 동일).
# 제외: macro_regime_history, orders, reservations, tax_*, backtest_jobs,
#       market_board_*, advisory_cache.
_TARGET_TABLES = [
    "page_views",
    "ai_usage_log",
    "audit_log",
    "recommendation_history",
    "daily_reports",
    "advisory_reports",
    "portfolio_reports",
    "semi_signals",
    "semi_indicator_values",
]


def _measure_tables(engine) -> dict[str, dict]:
    """대상 테이블별 row count (+ PostgreSQL이면 크기) 실측."""
    from sqlalchemy import text

    is_pg = engine.dialect.name == "postgresql"
    result: dict[str, dict] = {}
    with engine.connect() as conn:
        for table in _TARGET_TABLES:
            try:
                row_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
            except Exception as exc:
                logger.warning(f"{table} row count 조회 실패: {exc}")
                row_count = None

            size_bytes = None
            if is_pg:
                try:
                    size_bytes = conn.execute(
                        text("SELECT pg_total_relation_size(:t)"), {"t": table}
                    ).scalar()
                except Exception as exc:
                    logger.warning(f"{table} pg_total_relation_size 조회 실패: {exc}")

            result[table] = {"row_count": row_count, "size_bytes": size_bytes}
    return result


def _fmt_size(size_bytes) -> str:
    if size_bytes is None:
        return "N/A"
    mb = size_bytes / (1024 * 1024)
    return f"{mb:.2f} MB"


def _log_measurements(label: str, measurements: dict[str, dict]) -> None:
    logger.info(f"── {label} 실측 ──")
    for table, m in measurements.items():
        logger.info(
            f"  {table}: {m['row_count']}행, {_fmt_size(m['size_bytes'])}"
        )


def _run_vacuum(engine) -> None:
    """PostgreSQL: autocommit 연결에서 VACUUM (VERBOSE, ANALYZE) 전체 + page_views VACUUM FULL.
    SQLite: VACUUM;
    """
    from sqlalchemy import text

    dialect = engine.dialect.name
    if dialect == "postgresql":
        conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        try:
            logger.info("VACUUM (VERBOSE, ANALYZE) 실행 중...")
            conn.execute(text("VACUUM (VERBOSE, ANALYZE)"))
            logger.info("VACUUM FULL page_views 실행 중 (최대 누적 테이블, 짧은 exclusive lock)...")
            conn.execute(text("VACUUM FULL page_views"))
        finally:
            conn.close()
    elif dialect == "sqlite":
        conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        try:
            logger.info("VACUUM; 실행 중 (SQLite)...")
            conn.execute(text("VACUUM"))
        finally:
            conn.close()
    else:
        logger.warning(f"지원하지 않는 DB dialect({dialect}) — VACUUM 스킵")


def main() -> None:
    from db.session import engine
    from services.scheduler_service import _run_db_retention_cleanup_job

    logger.info(f"DB retention 백로그 1회 정리 시작 (dialect={engine.dialect.name})")

    before = _measure_tables(engine)
    _log_measurements("정리 전(before)", before)

    logger.info("retention cleanup 로직 실행 (Part B와 동일 로직 재사용)...")
    _run_db_retention_cleanup_job()

    _run_vacuum(engine)

    after = _measure_tables(engine)
    _log_measurements("정리 후(after)", after)

    logger.info("── 절감량 ──")
    for table in _TARGET_TABLES:
        b = before.get(table, {})
        a = after.get(table, {})
        b_rows, a_rows = b.get("row_count"), a.get("row_count")
        rows_diff = None
        if b_rows is not None and a_rows is not None:
            rows_diff = b_rows - a_rows
        b_size, a_size = b.get("size_bytes"), a.get("size_bytes")
        size_diff_str = ""
        if b_size is not None and a_size is not None:
            size_diff_str = f", 공간 {_fmt_size(b_size - a_size)} 회수"
        logger.info(f"  {table}: {rows_diff}행 삭제{size_diff_str}")

    logger.info("DB retention 백로그 1회 정리 완료")


if __name__ == "__main__":
    main()

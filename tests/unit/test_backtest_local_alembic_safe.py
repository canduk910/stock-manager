"""REQ-FIX-01: save_backtest_job alembic 미적용 graceful 처리 테스트.

운영 EC2에 `e1f2a3b4c5d6_add_backtest_symbols` 미적용 시 `BacktestJob.symbols` 컬럼 부재
→ `INSERT ... symbols=...` SQL 에러 → ServiceError 변환 회피 → raw 500.

본 fix:
- `BacktestRepository.create_job()` 가 `OperationalError`(미정의 컬럼) 캐치 후
  symbols 키를 제외하고 1회 재시도 → graceful 동작.
- `run_local_backtest` 가 save_backtest_job SQL 에러 시 ServiceError 로 변환.

본 테스트는 PostgreSQL 미가동 환경에서도 단위 검증되도록
SQLite 인메모리 엔진 + monkeypatch 만 사용한다.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from db.base import Base
from db.repositories.backtest_repo import BacktestRepository


@pytest.fixture
def sqlite_session():
    """alembic 컬럼 graceful 검증 전용 인메모리 SQLite 세션."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
    engine.dispose()


def test_create_job_with_symbols_normal(sqlite_session):
    """(a) symbols 컬럼 존재 환경 → symbols JSON 정상 저장."""
    repo = BacktestRepository(sqlite_session)
    out = repo.create_job(
        user_id=1,
        job_id="job-norm-1",
        strategy_name="momentum",
        symbol="005930",
        market="KR",
        strategy_type="local",
        submitted_at="2026-05-09T10:00:00+09:00",
        params=None,
        strategy_display_name="모멘텀",
        symbols=["005930", "000660"],
    )
    sqlite_session.commit()
    assert out["job_id"] == "job-norm-1"
    assert out["symbols"] == ["005930", "000660"]


def test_create_job_graceful_when_symbols_column_missing(sqlite_session, monkeypatch):
    """(b) `symbols` 컬럼 부재(alembic 미적용) 시 graceful — symbols 누락하고 INSERT.

    SQLAlchemy `OperationalError`("column symbols of relation backtest_jobs does not exist")
    를 시뮬레이션 → 재시도 시 symbols 제외 → 정상 저장.
    """
    repo = BacktestRepository(sqlite_session)

    call_count = {"n": 0}
    orig_flush = sqlite_session.flush

    def fake_flush(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # 첫 호출: 컬럼 부재 에러 시뮬레이션
            raise OperationalError(
                "INSERT INTO backtest_jobs ...",
                {},
                Exception('column "symbols" of relation "backtest_jobs" does not exist'),
            )
        return orig_flush(*args, **kwargs)

    monkeypatch.setattr(sqlite_session, "flush", fake_flush)

    out = repo.create_job(
        user_id=1,
        job_id="job-graceful-1",
        strategy_name="momentum",
        symbol="005930",
        market="KR",
        strategy_type="local",
        submitted_at="2026-05-09T10:00:00+09:00",
        symbols=["005930", "000660"],
    )
    sqlite_session.commit()

    # graceful 환경에선 symbols 응답이 None이어도 허용 (컬럼 부재 = 미저장)
    assert out["job_id"] == "job-graceful-1"
    assert call_count["n"] >= 2  # 첫 시도 fail + 재시도


def test_create_job_other_sql_error_propagates(sqlite_session, monkeypatch):
    """(c) 다른 SQL 에러(다른 컬럼)는 graceful 재시도 대상 아님 — 그대로 raise."""
    repo = BacktestRepository(sqlite_session)

    def fake_flush(*args, **kwargs):
        raise OperationalError(
            "INSERT INTO backtest_jobs ...",
            {},
            Exception("violates not-null constraint on column user_id"),
        )

    monkeypatch.setattr(sqlite_session, "flush", fake_flush)

    with pytest.raises(OperationalError):
        repo.create_job(
            user_id=1,
            job_id="job-fail-1",
            strategy_name="momentum",
            symbol="005930",
            market="KR",
            strategy_type="local",
            submitted_at="2026-05-09T10:00:00+09:00",
            symbols=["005930"],
        )


def test_run_local_backtest_save_db_error_wrapped_as_service_error(monkeypatch):
    """(d) `run_local_backtest` 가 save 단계 SQL 에러 시 ServiceError 로 변환 (raw 500 방지)."""
    from services import backtest_service
    from services.exceptions import ServiceError

    def fake_save(**kwargs):
        raise OperationalError(
            "INSERT INTO backtest_jobs ...",
            {},
            Exception("relation backtest_jobs does not exist"),
        )

    monkeypatch.setattr(
        backtest_service.strategy_store, "save_backtest_job", fake_save
    )

    with pytest.raises(ServiceError) as exc:
        backtest_service.run_local_backtest(
            preset="momentum",
            symbols=["005930", "000660"],
            market="KR",
            start_date="2024-01-01",
            end_date="2024-12-31",
            user_id=1,
        )
    msg = exc.value.message if hasattr(exc.value, "message") else str(exc.value)
    assert ("백테스트 작업 등록 실패" in msg) or ("DB 마이그레이션" in msg)

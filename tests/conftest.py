"""공용 pytest fixtures.

테스트 DB: PostgreSQL (프로덕션과 동일 DBMS).
로컬: docker compose -f docker-compose.test.yml up -d
CI: GitHub Actions services.postgres
"""

import os
os.environ["TESTING"] = "1"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from db.base import Base
from db.session import get_db
from services.auth_deps import get_current_user, require_admin
import db.session as _db_session_mod

# 기본값: docker-compose.test.yml 기준 (포트 5433)
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://stocktest:stocktest@localhost:5433/stocktest",
)

# 테스트용 가짜 admin 사용자
_FAKE_ADMIN = {"id": 1, "username": "admin", "name": "관리자", "role": "admin"}


@pytest.fixture(scope="session")
def _test_engine():
    """테스트 세션 전체에서 공유하는 PostgreSQL 엔진."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


def _truncate_all(engine):
    """모든 테이블 데이터 삭제 (테스트 격리)."""
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture
def db_session(_test_engine):
    """PostgreSQL 세션 — 테스트 후 TRUNCATE로 격리."""
    Session = sessionmaker(bind=_test_engine)
    session = Session()
    yield session
    session.close()
    _truncate_all(_test_engine)


def _make_client(app, engine, *, override_auth=True):
    """TestClient — SessionLocal을 테스트 엔진으로 교체."""
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=engine)

    if override_auth:
        app.dependency_overrides[get_current_user] = lambda: _FAKE_ADMIN
        app.dependency_overrides[require_admin] = lambda: _FAKE_ADMIN

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    _db_session_mod.SessionLocal.configure(bind=orig_bind)
    _truncate_all(engine)


@pytest.fixture
def client(_test_engine):
    """FastAPI TestClient — PostgreSQL + 인증 자동 우회.

    기존 API 테스트가 수정 없이 통과하도록 get_current_user를 오버라이드.
    인증 자체를 테스트하려면 raw_client fixture 사용.
    """
    from main import app
    yield from _make_client(app, _test_engine, override_auth=True)


@pytest.fixture
def raw_client(_test_engine):
    """인증 오버라이드 없는 TestClient — 인증 테스트 전용."""
    from main import app
    yield from _make_client(app, _test_engine, override_auth=False)

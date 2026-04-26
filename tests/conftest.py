"""공용 pytest fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from db.base import Base
from db.session import get_db
from services.auth_deps import get_current_user, require_admin
import db.session as _db_session_mod

# 테스트용 가짜 admin 사용자
_FAKE_ADMIN = {"id": 1, "username": "admin", "name": "관리자", "role": "admin"}


@pytest.fixture
def db_session():
    """인메모리 SQLite 세션 — 테스트 간 격리."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _make_client(app, *, override_auth=True):
    """TestClient 생성 — SessionLocal 바인딩을 인메모리 DB로 교체."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    # SessionLocal의 바인딩을 테스트 엔진으로 교체
    # → get_session()과 get_db() 모두 이 엔진을 사용하게 됨
    orig_bind = _db_session_mod.SessionLocal.kw.get("bind")
    _db_session_mod.SessionLocal.configure(bind=engine)

    if override_auth:
        app.dependency_overrides[get_current_user] = lambda: _FAKE_ADMIN
        app.dependency_overrides[require_admin] = lambda: _FAKE_ADMIN

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    _db_session_mod.SessionLocal.configure(bind=orig_bind)
    engine.dispose()


@pytest.fixture
def client():
    """FastAPI TestClient — 인메모리 DB + 인증 자동 우회.

    기존 API 테스트가 수정 없이 통과하도록 get_current_user를 오버라이드.
    인증 자체를 테스트하려면 raw_client fixture 사용.
    """
    from main import app
    yield from _make_client(app, override_auth=True)


@pytest.fixture
def raw_client():
    """인증 오버라이드 없는 TestClient — 인증 테스트 전용."""
    from main import app
    yield from _make_client(app, override_auth=False)

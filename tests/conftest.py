"""공용 pytest fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from db.base import Base


@pytest.fixture
def db_session():
    """인메모리 SQLite 세션 — 테스트 간 격리."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def client():
    """FastAPI TestClient — API 엔드포인트 테스트용."""
    from main import app
    return TestClient(app)

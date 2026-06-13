"""Semiconductor module — SQLite in-memory fixture (PostgreSQL 컨테이너 불필요)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
import db.models  # noqa: F401 — 모든 ORM 모델 트리거 import


@pytest.fixture
def semi_db():
    """SQLite in-memory 세션. 테스트 단위 격리."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()

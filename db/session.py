"""SQLAlchemy engine, session factory, and dependency helpers.

- ``get_db()``  — FastAPI ``Depends`` 전용 generator.
- ``get_session()`` — Store 래퍼 전용 context-manager (commit+close 자동).
- SQLite 사용 시 WAL + busy_timeout 자동 설정.
"""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

_is_sqlite = "sqlite" in DATABASE_URL

# SQLite: DB 디렉토리 자동 생성 (fresh install 대응)
if _is_sqlite:
    _db_path = DATABASE_URL.replace("sqlite:///", "")
    Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# SQLite PRAGMA 자동 설정 (WAL + busy timeout)
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    if _is_sqlite:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()


def get_db():
    """FastAPI Depends 전용 — request 단위 session lifecycle."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_session():
    """Store 래퍼 전용 세션 (commit + close 자동)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

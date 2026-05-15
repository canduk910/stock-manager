"""user_kis_credentials.id SEQUENCE 보강 (PostgreSQL hotfix)

Revision ID: f1a2b3c4d5e6
Revises: e7f8a9b0c1d2
Create Date: 2026-05-16 07:50:00.000000

R1 후속 hotfix — e7f8a9b0c1d2 에서 ``id`` 컬럼을 ``add_column(autoincrement=True)``
로 추가했으나 PostgreSQL은 컬럼 추가 시점에는 SERIAL/SEQUENCE 를 자동 생성하지 않는다
(CREATE TABLE 시점에만 동작). 결과적으로 INSERT 시 id 명시 누락 → NULL → NotNullViolation
→ starlette ServerErrorMiddleware ``Internal Server Error`` 21 bytes 응답 결함.

본 마이그레이션은 PostgreSQL 에서 SEQUENCE 를 명시적으로 생성하고 컬럼 DEFAULT 에 연결한다.
- SQLite: no-op (ROWID 가 PK 와 자동 매핑되어 이미 작동).
- PostgreSQL: SEQUENCE 생성 + 컬럼 OWNED BY + DEFAULT nextval + 기존 max(id) 기반 setval.

downgrade: PostgreSQL 에서 DEFAULT 제거 + SEQUENCE drop (SQLite no-op).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SEQ_NAME = 'user_kis_credentials_id_seq'


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    # 1) SEQUENCE 생성 (idempotent — 이미 있으면 스킵)
    op.execute(f"CREATE SEQUENCE IF NOT EXISTS {_SEQ_NAME} OWNED BY user_kis_credentials.id")

    # 2) 컬럼 DEFAULT 연결
    op.execute(
        f"ALTER TABLE user_kis_credentials "
        f"ALTER COLUMN id SET DEFAULT nextval('{_SEQ_NAME}')"
    )

    # 3) 기존 row 의 max(id) + 1 로 SEQUENCE 재설정 — 신규 INSERT 충돌 방지
    op.execute(
        f"SELECT setval('{_SEQ_NAME}', "
        f"COALESCE((SELECT MAX(id) FROM user_kis_credentials), 0) + 1, false)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    op.execute("ALTER TABLE user_kis_credentials ALTER COLUMN id DROP DEFAULT")
    op.execute(f"DROP SEQUENCE IF EXISTS {_SEQ_NAME}")

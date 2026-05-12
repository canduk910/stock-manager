"""advisory_cache 공유 캐시 전환 — PK (user_id, code, market) → (code, market).

user_id 컬럼은 nullable=True로 유지 (1차 배포 안정화 후 drop. 롤백 안전성).

Revision ID: c1d2e3f4a5b6
Revises: a9b8c7d6e5f4
Create Date: 2026-05-12
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels = None
depends_on = None


def _dedupe_keep_latest(conn):
    """동일 (code, market)에 user_id 별로 중복 row가 있으면 updated_at 최신만 보존.

    멱등 — 두 번 실행해도 동일 결과.
    """
    dialect = conn.dialect.name
    if dialect == "postgresql":
        # PostgreSQL: ROW_NUMBER() 윈도우로 최신만 보존
        conn.execute(sa.text("""
            DELETE FROM advisory_cache
            WHERE ctid IN (
                SELECT ctid FROM (
                    SELECT ctid,
                           ROW_NUMBER() OVER (PARTITION BY code, market ORDER BY updated_at DESC NULLS LAST) AS rn
                    FROM advisory_cache
                ) sub
                WHERE rn > 1
            )
        """))
    else:
        # SQLite: rowid 기반
        conn.execute(sa.text("""
            DELETE FROM advisory_cache
            WHERE rowid NOT IN (
                SELECT rowid FROM (
                    SELECT rowid,
                           ROW_NUMBER() OVER (PARTITION BY code, market ORDER BY updated_at DESC) AS rn
                    FROM advisory_cache
                ) sub
                WHERE rn = 1
            )
        """))


def _current_pk_cols(conn) -> set:
    insp = sa.inspect(conn)
    pk = insp.get_pk_constraint("advisory_cache")
    return set(pk.get("constrained_columns") or [])


def upgrade() -> None:
    conn = op.get_bind()

    # 1) 동일 (code, market) 중복 제거 (멱등)
    _dedupe_keep_latest(conn)

    # 멱등 가드: 이미 새 PK 적용된 경우 skip
    if _current_pk_cols(conn) == {"code", "market"}:
        return

    dialect = conn.dialect.name

    # 2) PK 재정의: (user_id, code, market) → (code, market)
    if dialect == "postgresql":
        with op.batch_alter_table("advisory_cache", schema=None) as batch_op:
            batch_op.drop_constraint("advisory_cache_pkey", type_="primary")
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
            batch_op.create_primary_key("advisory_cache_pkey", ["code", "market"])
    else:
        # SQLite: PK constraint는 자동 이름이 없어 drop_constraint 불가.
        # batch_alter_table(recreate="always")로 테이블 재생성하면서 새 PK 적용.
        with op.batch_alter_table(
            "advisory_cache", schema=None, recreate="always"
        ) as batch_op:
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=True)
            batch_op.create_primary_key("pk_advisory_cache", ["code", "market"])


def downgrade() -> None:
    """PK 복원 — user_id 누락(NULL) row는 user_id=1로 채움."""
    conn = op.get_bind()

    # NULL user_id를 1로 보정 (다운그레이드 시 PK 복원 위해)
    conn.execute(sa.text("UPDATE advisory_cache SET user_id = 1 WHERE user_id IS NULL"))

    # 멱등 가드: 이미 옛 PK 상태면 skip
    if _current_pk_cols(conn) == {"user_id", "code", "market"}:
        return

    dialect = conn.dialect.name

    if dialect == "postgresql":
        with op.batch_alter_table("advisory_cache", schema=None) as batch_op:
            batch_op.drop_constraint("advisory_cache_pkey", type_="primary")
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_primary_key(
                "advisory_cache_pkey", ["user_id", "code", "market"]
            )
    else:
        with op.batch_alter_table(
            "advisory_cache", schema=None, recreate="always"
        ) as batch_op:
            batch_op.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_primary_key(
                "pk_advisory_cache", ["user_id", "code", "market"]
            )

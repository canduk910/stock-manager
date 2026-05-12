"""portfolio_reports에 user_id 컬럼 추가 + 백필.

멀티유저 환경에서 포트폴리오 자문 보고서를 사용자별로 격리한다.
- 현재 1명 가정 운영 중 → 기존 행은 모두 user_id=1로 백필 (안전).
- nullable=True + FK ondelete=SET NULL — admin 삭제 시 이력 자체는 보존.
- 인덱스 (user_id, generated_at) — 사용자별 이력 정렬용.

Revision ID: d4e5f6a7b8c9
Revises: c1d2e3f4a5b6
Create Date: 2026-05-12
"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def _has_column(conn, table: str, col: str) -> bool:
    insp = sa.inspect(conn)
    return any(c["name"] == col for c in insp.get_columns(table))


def _has_index(conn, table: str, idx: str) -> bool:
    insp = sa.inspect(conn)
    return any(i["name"] == idx for i in insp.get_indexes(table))


def upgrade() -> None:
    conn = op.get_bind()

    # 1) user_id 컬럼 추가 (멱등) — nullable=True
    if not _has_column(conn, "portfolio_reports", "user_id"):
        with op.batch_alter_table("portfolio_reports", schema=None) as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))

    # 2) 기존 행 백필 — user_id=1 (현재 admin 1명 가정 운영)
    conn.execute(sa.text(
        "UPDATE portfolio_reports SET user_id = 1 WHERE user_id IS NULL"
    ))

    # 3) FK 제약 추가 — users.id ondelete=SET NULL
    # batch_alter_table는 SQLite도 호환. PostgreSQL은 즉시 적용.
    # 이미 같은 이름의 FK가 있으면 SKIP (멱등).
    insp = sa.inspect(conn)
    existing_fks = {fk["name"] for fk in insp.get_foreign_keys("portfolio_reports")}
    fk_name = "fk_portfolio_reports_user_id"
    if fk_name not in existing_fks:
        try:
            with op.batch_alter_table("portfolio_reports", schema=None) as batch_op:
                batch_op.create_foreign_key(
                    fk_name, "users",
                    ["user_id"], ["id"],
                    ondelete="SET NULL",
                )
        except Exception:
            # users 테이블이 없거나 호환 이슈 — graceful pass (마이그레이션 멈춤 방지)
            pass

    # 4) 인덱스 추가 (멱등) — (user_id, generated_at)
    if not _has_index(conn, "portfolio_reports", "idx_portfolio_reports_user_created"):
        op.create_index(
            "idx_portfolio_reports_user_created",
            "portfolio_reports",
            ["user_id", "generated_at"],
        )


def downgrade() -> None:
    """롤백: 인덱스 + FK + 컬럼 제거."""
    conn = op.get_bind()

    if _has_index(conn, "portfolio_reports", "idx_portfolio_reports_user_created"):
        op.drop_index("idx_portfolio_reports_user_created", table_name="portfolio_reports")

    insp = sa.inspect(conn)
    existing_fks = {fk["name"] for fk in insp.get_foreign_keys("portfolio_reports")}
    if "fk_portfolio_reports_user_id" in existing_fks:
        try:
            with op.batch_alter_table("portfolio_reports", schema=None) as batch_op:
                batch_op.drop_constraint("fk_portfolio_reports_user_id", type_="foreignkey")
        except Exception:
            pass

    if _has_column(conn, "portfolio_reports", "user_id"):
        with op.batch_alter_table("portfolio_reports", schema=None) as batch_op:
            batch_op.drop_column("user_id")

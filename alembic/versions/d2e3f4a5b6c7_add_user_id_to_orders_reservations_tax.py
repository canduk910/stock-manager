"""add user_id to orders/reservations/tax_* tables

Revision ID: d2e3f4a5b6c7
Revises: d1e2f3a4b5c6
Create Date: 2026-05-03 09:30:00.000000

Phase 4 D.3 — 사용자별 자산관리 데이터 격리.
NULL 허용 — 기존 데이터는 NULL로 남겨두고, 신규 작성분부터 user_id 매핑.
admin이 본인 KIS 등록 후 자동 매핑 안 함(데이터 정합성 보호).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TARGETS = [
    ("orders", "idx_orders_user_id"),
    ("reservations", "idx_reservations_user_id"),
    ("tax_transactions", "idx_tax_transactions_user_id"),
    ("tax_calculations", "idx_tax_calculations_user_id"),
    ("tax_fifo_lots", "idx_tax_fifo_lots_user_id"),
]


def upgrade() -> None:
    for table, idx in _TARGETS:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
            batch_op.create_index(idx, ["user_id"], unique=False)


def downgrade() -> None:
    for table, idx in reversed(_TARGETS):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(idx)
            batch_op.drop_column("user_id")

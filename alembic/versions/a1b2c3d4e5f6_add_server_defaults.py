"""Add server_default to orders and reservations columns.

Revision ID: a1b2c3d4e5f6
Revises: f717b65d0d31
Create Date: 2026-04-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f717b65d0d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # orders 테이블
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column("filled_quantity", server_default=sa.text("0"))
        batch_op.alter_column("status", server_default=sa.text("'PLACED'"))
        batch_op.alter_column("currency", server_default=sa.text("'KRW'"))
        batch_op.alter_column("memo", server_default=sa.text("''"))

    # reservations 테이블
    with op.batch_alter_table("reservations", schema=None) as batch_op:
        batch_op.alter_column("market", server_default=sa.text("'KR'"))
        batch_op.alter_column("status", server_default=sa.text("'WAITING'"))
        batch_op.alter_column("memo", server_default=sa.text("''"))


def downgrade() -> None:
    with op.batch_alter_table("reservations", schema=None) as batch_op:
        batch_op.alter_column("memo", server_default=None)
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("market", server_default=None)

    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.alter_column("memo", server_default=None)
        batch_op.alter_column("currency", server_default=None)
        batch_op.alter_column("status", server_default=None)
        batch_op.alter_column("filled_quantity", server_default=None)

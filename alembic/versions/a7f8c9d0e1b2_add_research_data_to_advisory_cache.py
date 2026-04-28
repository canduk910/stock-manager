"""Add research_data column to advisory_cache.

Revision ID: a7f8c9d0e1b2
Revises: b1c2d3e4f5a6
Create Date: 2026-04-28
"""

from alembic import op
import sqlalchemy as sa

revision = "a7f8c9d0e1b2"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("advisory_cache", schema=None) as batch_op:
        batch_op.add_column(sa.Column("research_data", sa.JSON, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("advisory_cache", schema=None) as batch_op:
        batch_op.drop_column("research_data")

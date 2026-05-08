"""add exchange column to stock_info

Revision ID: e4f5a6b7c8d9
Revises: d3f4a5b6c7d8
Create Date: 2026-05-08 12:00:00.000000

REQ-DB-02: stock_info.exchange (VARCHAR(8) NULL) — 미국 거래소(NAS/NYS/AMS) 캐시.
무손실 마이그레이션. NULLABLE, 기본값 없음.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'stock_info',
        sa.Column('exchange', sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('stock_info', 'exchange')

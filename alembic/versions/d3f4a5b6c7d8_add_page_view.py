"""add page_views table

Revision ID: d3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-05-03 10:00:00.000000

Phase 4 단계 5 (C) — 페이지별 이용현황 통계.
FastAPI 미들웨어에서 비동기 INSERT.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3f4a5b6c7d8'
down_revision: Union[str, Sequence[str], None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'page_views',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('duration_ms', sa.Float(), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_page_views_user_id', 'page_views', ['user_id'])
    op.create_index('idx_page_views_path_created', 'page_views', ['path', 'created_at'])
    op.create_index('idx_page_views_created', 'page_views', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_page_views_created', table_name='page_views')
    op.drop_index('idx_page_views_path_created', table_name='page_views')
    op.drop_index('ix_page_views_user_id', table_name='page_views')
    op.drop_table('page_views')

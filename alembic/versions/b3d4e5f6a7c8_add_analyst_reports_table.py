"""add analyst_reports table

Revision ID: b3d4e5f6a7c8
Revises: 9cda1c3787e5
Create Date: 2026-05-01 09:00:00.000000

REQ-ANALYST-06: 증권사 리포트 메타데이터 + PDF 요약 + 시간축 추이 영속화.
유니크 인덱스 (code, market, broker, published_at, title)로 중복 방지.
target_price BigInteger (KR 메가캡 25억원 수준 대응).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3d4e5f6a7c8'
down_revision: Union[str, Sequence[str], None] = '9cda1c3787e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'analyst_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('market', sa.String(), nullable=False, server_default='KR'),
        sa.Column('broker', sa.String(), nullable=False),
        sa.Column('target_price', sa.BigInteger(), nullable=True),
        sa.Column('opinion', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False, server_default=''),
        sa.Column('pdf_url', sa.String(), nullable=False, server_default=''),
        sa.Column('summary', sa.Text(), nullable=False, server_default=''),
        sa.Column('published_at', sa.String(), nullable=False),
        sa.Column('fetched_at', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'code', 'market', 'broker', 'published_at', 'title',
            name='uq_analyst_reports_unique',
        ),
    )
    op.create_index(
        'idx_analyst_reports_code_market_pub',
        'analyst_reports',
        ['code', 'market', 'published_at'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_analyst_reports_code_market_pub', table_name='analyst_reports')
    op.drop_table('analyst_reports')

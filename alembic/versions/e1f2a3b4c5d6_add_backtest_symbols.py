"""add backtest_jobs.symbols JSON column

Revision ID: e1f2a3b4c5d6
Revises: d3f4a5b6c7d8
Create Date: 2026-05-08 00:00:00.000000

다중 종목 로컬 백테스트(`local_backtest` 패키지) 지원.
기존 `symbol` 컬럼은 캐싱/조회 호환을 위해 첫 종목으로 유지하고,
신규 `symbols` JSON 컬럼에 전체 종목 list[str] 저장.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd3f4a5b6c7d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'backtest_jobs',
        sa.Column('symbols', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('backtest_jobs', 'symbols')

"""add backtest_jobs.mcp_job_id (fire-and-poll merge)

Revision ID: a9b8c7d6e5f4
Revises: ('e4f5a6b7c8d9', 'f5a6b7c8d9e0')
Create Date: 2026-05-09 00:00:00.000000

MCP backtester 측 job_id 영속화. fire-and-poll 패턴 도입(2026-05-09)으로
POST /api/backtest/run/preset 즉시 응답 + GET /result/{job_id}에서
DB 행의 mcp_job_id로 MCP `get_backtest_result_tool(wait=False)` lazy poll.

기존 동시 다중 head(e4f5a6b7c8d9 stock_info.exchange + f5a6b7c8d9e0
orders.exchange)도 본 revision에서 merge.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = ('e4f5a6b7c8d9', 'f5a6b7c8d9e0')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'backtest_jobs',
        sa.Column('mcp_job_id', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('backtest_jobs', 'mcp_job_id')

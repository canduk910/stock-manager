"""add semiconductor indicators (Phase 1) + seed thresholds

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-06-13 09:30:00.000000

반도체 사이클 선행지표 모니터링 모듈 Phase 1.
- semi_indicator_values: 시계열 raw
- semi_signals: 상태 변경 이력
- semi_thresholds: 임계값 (관리자 편집)
- 기본 임계값 seed 8건
"""
from datetime import datetime, timedelta, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_KST = timezone(timedelta(hours=9))


def _now_kst_iso() -> str:
    return datetime.now(_KST).isoformat(timespec="seconds")


def upgrade() -> None:
    """Upgrade schema."""
    # ── semi_indicator_values ─────────────────────────────────
    op.create_table(
        'semi_indicator_values',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('indicator_name', sa.String(length=64), nullable=False),
        sa.Column('observed_at', sa.String(length=10), nullable=False),
        sa.Column('value', sa.JSON(), nullable=True),
        sa.Column('value_meta', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=128), nullable=False),
        sa.Column('collected_at', sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_name', 'observed_at', name='uq_semi_indicator_obs'),
    )
    with op.batch_alter_table('semi_indicator_values', schema=None) as batch_op:
        batch_op.create_index(
            'idx_semi_indicator_obs_desc',
            ['indicator_name', 'observed_at'],
            unique=False,
        )

    # ── semi_signals ──────────────────────────────────────────
    op.create_table(
        'semi_signals',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('indicator_name', sa.String(length=64), nullable=False),
        sa.Column('fired_at', sa.String(length=32), nullable=False),
        sa.Column('level', sa.String(length=16), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('value_snapshot', sa.JSON(), nullable=False),
        sa.Column('ack', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('semi_signals', schema=None) as batch_op:
        batch_op.create_index(
            'idx_semi_signals_indicator_fired',
            ['indicator_name', 'fired_at'],
            unique=False,
        )
        batch_op.create_index('idx_semi_signals_fired', ['fired_at'], unique=False)

    # ── semi_thresholds ───────────────────────────────────────
    op.create_table(
        'semi_thresholds',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('indicator_name', sa.String(length=64), nullable=False),
        sa.Column('threshold_key', sa.String(length=64), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.String(length=32), nullable=False),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('indicator_name', 'threshold_key', name='uq_semi_threshold_key'),
    )

    # ── Seed 기본 임계값 (Phase 1 확정) ────────────────────────
    now = _now_kst_iso()
    seeds = [
        # hyperscaler_capex
        ("hyperscaler_capex", "yoy_warning_pct", -5.0, "2분기 연속 YoY ≤ -5% → WARNING"),
        ("hyperscaler_capex", "yoy_alert_pct", -15.0, "단일 분기 YoY ≤ -15% → ALERT"),
        # memory_inventory
        ("memory_inventory", "days_warning_increase_qtr", 2, "N분기 연속 증가 → WARNING"),
        ("memory_inventory", "days_alert_threshold", 120.0, "절대값 ≥ 120일 → ALERT"),
        # hbm_contracts
        (
            "hbm_contracts",
            "keyword_regex",
            "HBM|장기공급|메모리.{0,10}공급계약",
            "report_nm 2차 정규식 매칭 (re.IGNORECASE). 관리자가 DB에서 즉시 확장 가능.",
        ),
        # ai_ipo
        ("ai_ipo", "loss_pct_warning", -20.0, "수익률 ≤ -20% → WARNING (티커당)"),
        ("ai_ipo", "lockup_dminus_days", 7, "락업 해제 D-N 이내 → INFO"),
        # market_breadth
        ("market_breadth", "adr20_warning", 0.8, "ADR(20) < 0.8 + KOSPI 252일 신고 → WARNING"),
    ]
    semi_thresholds = sa.table(
        'semi_thresholds',
        sa.column('indicator_name', sa.String),
        sa.column('threshold_key', sa.String),
        sa.column('value', sa.JSON),
        sa.column('comment', sa.Text),
        sa.column('updated_at', sa.String),
        sa.column('updated_by', sa.Integer),
    )
    op.bulk_insert(
        semi_thresholds,
        [
            {
                "indicator_name": name,
                "threshold_key": key,
                "value": val,
                "comment": comment,
                "updated_at": now,
                "updated_by": None,
            }
            for (name, key, val, comment) in seeds
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('semi_signals', schema=None) as batch_op:
        batch_op.drop_index('idx_semi_signals_fired')
        batch_op.drop_index('idx_semi_signals_indicator_fired')
    with op.batch_alter_table('semi_indicator_values', schema=None) as batch_op:
        batch_op.drop_index('idx_semi_indicator_obs_desc')
    op.drop_table('semi_thresholds')
    op.drop_table('semi_signals')
    op.drop_table('semi_indicator_values')

"""add orders.exchange column for KRX+NXT routing

Revision ID: f5a6b7c8d9e0
Revises: e1f2a3b4c5d6
Create Date: 2026-05-08 12:00:00.000000

KRX+NXT 통합시세 + SOR (2026-05-08).
신규 주문은 SOR/KRX/NXT 셀렉터 → KIS 응답 ORD_EXG_GB로 SOR-KRX/SOR-NXT 정밀 갱신.
NULL 허용 — 기존 데이터는 NULL로 유지, to_dict() 변환 시 'KRX'로 폴백.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("exchange", sa.String(length=16), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("exchange")

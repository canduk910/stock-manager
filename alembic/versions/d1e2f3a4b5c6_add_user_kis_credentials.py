"""add user_kis_credentials table

Revision ID: d1e2f3a4b5c6
Revises: b3d4e5f6a7c8
Create Date: 2026-05-03 09:00:00.000000

Phase 4 D.1 — 사용자별 KIS 자격증명 저장 (AES-GCM 암호화).
1:1 관계 (user_id PK + FK→users.id ON DELETE CASCADE).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'b3d4e5f6a7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_kis_credentials',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('app_key_enc', sa.String(), nullable=False),
        sa.Column('app_secret_enc', sa.String(), nullable=False),
        sa.Column('acnt_no_enc', sa.String(), nullable=False),
        sa.Column('acnt_prdt_cd_stk', sa.String(), nullable=False),
        sa.Column('acnt_prdt_cd_fno', sa.String(), nullable=True),
        sa.Column('hts_id', sa.String(), nullable=True),
        sa.Column(
            'base_url',
            sa.String(),
            nullable=False,
            server_default='https://openapi.koreainvestment.com:9443',
        ),
        sa.Column('validated_at', sa.String(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=False, server_default=''),
        sa.Column('updated_at', sa.String(), nullable=False, server_default=''),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            ondelete='CASCADE',
            name='fk_user_kis_credentials_user_id',
        ),
        sa.PrimaryKeyConstraint('user_id', name='pk_user_kis_credentials'),
    )


def downgrade() -> None:
    op.drop_table('user_kis_credentials')

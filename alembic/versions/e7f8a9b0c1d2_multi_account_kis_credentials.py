"""multi-account KIS credentials (R1)

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-05-15 21:50:00.000000

R1 (KIS 멀티 계좌 지원):
- user_kis_credentials PK 를 user_id 단독 → id AUTO_INCREMENT 로 전환.
- label VARCHAR(50) NOT NULL + is_default BOOLEAN NOT NULL 컬럼 추가.
- UNIQUE(user_id, label).
- 기존 1행 사용자 → label='기본', is_default=true 로 보존 변환.
- orders / reservations 에 account_label VARCHAR(50) NULL + (user_id, account_label) 인덱스 추가.

마이그레이션 무결성:
- 기존 row 의 account_label 은 NULL 보존 (NOT NULL 강제 금지) — default 폴백 동작.
- entrypoint.sh / lifespan `alembic upgrade head` 자동 실행에서 graceful 처리.

downgrade:
- is_default=true 행 하나만 살리고 나머지 user_kis_credentials 행은 삭제 (데이터 손실).
- PK 를 user_id 단독으로 복원.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ── user_kis_credentials 스키마 재설계 ──────────────────────────────────
    # 1) 컬럼 추가 (server_default 로 기존 row 백필)
    with op.batch_alter_table('user_kis_credentials', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('id', sa.Integer(), nullable=True, autoincrement=True)
        )
        batch_op.add_column(
            sa.Column('label', sa.String(length=50), nullable=False, server_default='기본')
        )
        batch_op.add_column(
            sa.Column(
                'is_default',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('true'),
            )
        )

    # 2) id 컬럼 백필 (PostgreSQL: SEQUENCE / SQLite: ROWID)
    if dialect == 'postgresql':
        # 기존 행에 id 부여 (FK 없으므로 단순 ROW_NUMBER)
        op.execute(
            "UPDATE user_kis_credentials t SET id = sub.rn "
            "FROM (SELECT user_id, ROW_NUMBER() OVER (ORDER BY user_id) AS rn "
            "      FROM user_kis_credentials) sub "
            "WHERE t.user_id = sub.user_id"
        )
    elif dialect == 'sqlite':
        # SQLite: rowid 로 매핑 — batch_alter_table 이 recreate 시 자동 처리.
        op.execute("UPDATE user_kis_credentials SET id = rowid WHERE id IS NULL")
    else:
        # 기타 DB는 best-effort
        op.execute("UPDATE user_kis_credentials SET id = 1 WHERE id IS NULL")

    # 3) PK 재구성: user_id 단독 PK 폐기 → id PK + UNIQUE(user_id, label)
    with op.batch_alter_table('user_kis_credentials', schema=None) as batch_op:
        # 기존 user_id 단독 PK 폐기
        batch_op.drop_constraint('pk_user_kis_credentials', type_='primary')
        # id 컬럼 NOT NULL + PK 부여
        batch_op.alter_column('id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_primary_key('pk_user_kis_credentials', ['id'])
        batch_op.create_unique_constraint(
            'uq_user_kis_credentials_user_label',
            ['user_id', 'label'],
        )
        batch_op.create_index(
            'ix_user_kis_credentials_user_id',
            ['user_id'],
        )

    # 4) PostgreSQL 의 경우 id 시퀀스를 max(id) 다음으로 재설정.
    if dialect == 'postgresql':
        op.execute(
            "SELECT setval(pg_get_serial_sequence('user_kis_credentials', 'id'), "
            "COALESCE((SELECT MAX(id) FROM user_kis_credentials), 1))"
        )

    # ── orders.account_label 추가 ───────────────────────────────────────────
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_label', sa.String(length=50), nullable=True))
        batch_op.create_index('idx_orders_user_account', ['user_id', 'account_label'])

    # ── reservations.account_label 추가 ────────────────────────────────────
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('account_label', sa.String(length=50), nullable=True))
        batch_op.create_index('idx_reservations_user_account', ['user_id', 'account_label'])


def downgrade() -> None:
    """downgrade — 데이터 손실 경고.

    user_kis_credentials 의 is_default=true 행 하나만 살리고 나머지는 삭제 후
    user_id 단독 PK 로 복원한다. 사용자가 추가 등록한 라벨 계좌는 영구 손실.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ── reservations / orders 컬럼 제거 ─────────────────────────────────────
    with op.batch_alter_table('reservations', schema=None) as batch_op:
        batch_op.drop_index('idx_reservations_user_account')
        batch_op.drop_column('account_label')

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index('idx_orders_user_account')
        batch_op.drop_column('account_label')

    # ── user_kis_credentials 단일 row 복원 ─────────────────────────────────
    # 1) 사용자당 default 행만 살리고 다른 행 삭제 (데이터 손실).
    op.execute(
        "DELETE FROM user_kis_credentials WHERE id NOT IN ("
        "  SELECT MIN(id) FROM user_kis_credentials "
        "  WHERE is_default = true GROUP BY user_id"
        ")"
    )

    with op.batch_alter_table('user_kis_credentials', schema=None) as batch_op:
        batch_op.drop_index('ix_user_kis_credentials_user_id')
        batch_op.drop_constraint('uq_user_kis_credentials_user_label', type_='unique')
        batch_op.drop_constraint('pk_user_kis_credentials', type_='primary')
        batch_op.drop_column('id')
        batch_op.drop_column('is_default')
        batch_op.drop_column('label')
        batch_op.create_primary_key('pk_user_kis_credentials', ['user_id'])

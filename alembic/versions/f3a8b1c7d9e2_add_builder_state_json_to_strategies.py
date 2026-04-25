"""add builder_state_json to strategies

Revision ID: f3a8b1c7d9e2
Revises: ebdfc36d2ef3
Create Date: 2026-04-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a8b1c7d9e2'
down_revision: Union[str, Sequence[str], None] = 'ebdfc36d2ef3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('strategies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('builder_state_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('strategies', schema=None) as batch_op:
        batch_op.drop_column('builder_state_json')

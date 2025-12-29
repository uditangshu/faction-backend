"""Add user_badges table

Revision ID: h3c4d5e6f7g8
Revises: g2b3c4d5e6f7
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'h3c4d5e6f7g8'
down_revision: Union[str, None] = 'g2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('user_badges',
        sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('badge_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('earned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_seen', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['badge_id'], ['badges.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'badge_id')
    )
    op.create_index(op.f('ix_user_badges_user_id'), 'user_badges', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_badges_badge_id'), 'user_badges', ['badge_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_badges_badge_id'), table_name='user_badges')
    op.drop_index(op.f('ix_user_badges_user_id'), table_name='user_badges')
    op.drop_table('user_badges')

"""add_index_on_questions_is_active

Revision ID: bcc65753e21d
Revises: d2d0ed24df00
Create Date: 2025-11-25 18:43:40.774331

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcc65753e21d'
down_revision: Union[str, None] = 'd2d0ed24df00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add index on is_active column for faster filtering
    op.create_index('ix_questions_is_active', 'questions', ['is_active'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_questions_is_active', table_name='questions')

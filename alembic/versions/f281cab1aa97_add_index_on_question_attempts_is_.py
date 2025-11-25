"""add_index_on_question_attempts_is_correct

Revision ID: f281cab1aa97
Revises: bcc65753e21d
Create Date: 2025-11-25 18:48:27.395972

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f281cab1aa97'
down_revision: Union[str, None] = 'bcc65753e21d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add composite index on (user_id, is_correct) for faster correct attempt counting
    op.create_index('ix_question_attempts_user_id_is_correct', 'question_attempts', ['user_id', 'is_correct'], unique=False)
    # Also add index on is_correct alone for general queries
    op.create_index('ix_question_attempts_is_correct', 'question_attempts', ['is_correct'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_question_attempts_is_correct', table_name='question_attempts')
    op.drop_index('ix_question_attempts_user_id_is_correct', table_name='question_attempts')

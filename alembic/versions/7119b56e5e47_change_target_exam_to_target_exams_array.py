"""change target_exam to target_exams array

Revision ID: 7119b56e5e47
Revises: 0d13a7dacaa4
Create Date: 2025-11-23 20:42:43.370986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7119b56e5e47'
down_revision: Union[str, None] = '0d13a7dacaa4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the old target_exam column (ENUM)
    op.drop_column('users', 'target_exam')
    
    # Add new target_exams column (JSON array)
    op.add_column('users', sa.Column('target_exams', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the new target_exams column
    op.drop_column('users', 'target_exams')
    
    # Re-add the old target_exam column (ENUM)
    op.add_column('users', sa.Column('target_exam', sa.Enum('JEE_ADVANCED', 'JEE_MAINS', 'NEET', 'OLYMPIAD', 'CBSE', name='targetexam'), nullable=False))

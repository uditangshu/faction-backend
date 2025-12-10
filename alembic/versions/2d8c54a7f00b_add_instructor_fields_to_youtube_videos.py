"""add_instructor_fields_to_youtube_videos

Revision ID: 2d8c54a7f00b
Revises: b97bef5cc5e1
Create Date: 2025-12-10 22:13:42.313153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d8c54a7f00b'
down_revision: Union[str, None] = 'b97bef5cc5e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add instructor_name and instructor_institution columns to youtube_videos table
    op.add_column('youtube_videos', sa.Column('instructor_name', sa.String(length=100), nullable=True))
    op.add_column('youtube_videos', sa.Column('instructor_institution', sa.String(length=100), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove instructor_name and instructor_institution columns from youtube_videos table
    op.drop_column('youtube_videos', 'instructor_institution')
    op.drop_column('youtube_videos', 'instructor_name')

"""add bookmarked videos table

Revision ID: g2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2025-12-25 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision = 'g2b3c4d5e6f7'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create bookmarked_videos table
    op.create_table(
        'bookmarked_videos',
        sa.Column('id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('user_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('youtube_video_id', sqlmodel.sql.sqltypes.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['youtube_video_id'], ['youtube_videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'youtube_video_id', name='unique_user_video_bookmark')
    )
    
    # Create indexes
    op.create_index('ix_bookmarked_videos_user_id', 'bookmarked_videos', ['user_id'])
    op.create_index('ix_bookmarked_videos_youtube_video_id', 'bookmarked_videos', ['youtube_video_id'])
    op.create_index('ix_bookmarked_videos_created_at', 'bookmarked_videos', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_bookmarked_videos_created_at', table_name='bookmarked_videos')
    op.drop_index('ix_bookmarked_videos_youtube_video_id', table_name='bookmarked_videos')
    op.drop_index('ix_bookmarked_videos_user_id', table_name='bookmarked_videos')
    
    # Drop table
    op.drop_table('bookmarked_videos')

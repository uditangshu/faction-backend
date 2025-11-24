"""merge_push_token_heads

Revision ID: 88f83eb3e6c3
Revises: 5daecb2ae85d, f98e7b489caa
Create Date: 2025-11-24 14:11:34.510383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '88f83eb3e6c3'
down_revision: Union[str, None] = ('5daecb2ae85d', 'f98e7b489caa')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

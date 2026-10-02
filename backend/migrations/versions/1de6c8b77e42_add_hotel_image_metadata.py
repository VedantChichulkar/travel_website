"""add hotel image upload metadata

Revision ID: 1de6c8b77e42
Revises: 9c71bf6ee2b4
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "1de6c8b77e42"
down_revision: Union[str, Sequence[str], None] = "9c71bf6ee2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("hotel_images", sa.Column("storage_key", sa.String(length=512), nullable=True))
    op.add_column("hotel_images", sa.Column("content_type", sa.String(length=100), nullable=True))
    op.add_column("hotel_images", sa.Column("file_size", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("hotel_images", "file_size")
    op.drop_column("hotel_images", "content_type")
    op.drop_column("hotel_images", "storage_key")

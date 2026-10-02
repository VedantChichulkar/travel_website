"""add persisted hotel partner profile completion

Revision ID: 9c71bf6ee2b4
Revises: b7410cd92341
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c71bf6ee2b4"
down_revision: Union[str, Sequence[str], None] = "b7410cd92341"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("hotels", sa.Column("profile_completion_percent", sa.Integer(), server_default="0", nullable=False))
    op.add_column("hotels", sa.Column("is_profile_complete", sa.Boolean(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("hotels", "is_profile_complete")
    op.drop_column("hotels", "profile_completion_percent")

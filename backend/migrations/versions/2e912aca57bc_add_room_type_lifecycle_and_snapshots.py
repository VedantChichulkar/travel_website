"""add room type lifecycle and snapshots

Revision ID: 2e912aca57bc
Revises: 1de6c8b77e42
Create Date: 2026-09-13 18:33:48.137881

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '2e912aca57bc'
down_revision: Union[str, Sequence[str], None] = '1de6c8b77e42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('room_types', sa.Column('status', sa.Enum('DRAFT', 'PENDING', 'APPROVED', 'NEEDS_CHANGES', 'BOOKABLE', name='room_type_status', native_enum=False), server_default='DRAFT', nullable=False))
    op.add_column('room_types', sa.Column('extra_bed_rules', sa.Text(), nullable=True))
    op.add_column('room_types', sa.Column('meal_add_on_options', sa.JSON(), nullable=False))
    op.add_column('room_types', sa.Column('review_notes', sa.Text(), nullable=True))
    op.add_column('room_types', sa.Column('reviewed_by', sa.Integer(), nullable=True))
    op.add_column('room_types', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('room_types', sa.Column('version', sa.Integer(), server_default='1', nullable=False))
    op.create_index(op.f('ix_room_types_reviewed_by'), 'room_types', ['reviewed_by'], unique=False)
    op.create_index(op.f('ix_room_types_status'), 'room_types', ['status'], unique=False)
    op.create_foreign_key('fk_room_types_reviewed_by', 'room_types', 'users', ['reviewed_by'], ['id'], ondelete='SET NULL')
    op.create_table(
        'room_type_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('room_type_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('reason', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['room_type_id'], ['room_types.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_room_type_versions_room_type_id'), 'room_type_versions', ['room_type_id'], unique=False)
    op.alter_column('users', 'role',
               existing_type=mysql.ENUM('USER', 'ADMIN', collation='utf8mb4_unicode_ci'),
               type_=sa.Enum('CUSTOMER', 'HOTEL_PARTNER', 'ADMIN', 'USER', name='user_role', native_enum=False),
               existing_nullable=False,
               existing_server_default=sa.text("'USER'"))
    op.alter_column('users', 'status',
               existing_type=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=20),
               type_=sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', name='user_status', native_enum=False),
               existing_nullable=False,
               existing_server_default=sa.text("'ACTIVE'"))


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'status',
               existing_type=sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', name='user_status', native_enum=False),
               type_=mysql.VARCHAR(collation='utf8mb4_unicode_ci', length=20),
               existing_nullable=False,
               existing_server_default=sa.text("'ACTIVE'"))
    op.alter_column('users', 'role',
               existing_type=sa.Enum('CUSTOMER', 'HOTEL_PARTNER', 'ADMIN', 'USER', name='user_role', native_enum=False),
               type_=mysql.ENUM('USER', 'ADMIN', collation='utf8mb4_unicode_ci'),
               existing_nullable=False,
               existing_server_default=sa.text("'USER'"))
    op.drop_index(op.f('ix_room_type_versions_room_type_id'), table_name='room_type_versions')
    op.drop_table('room_type_versions')
    op.drop_constraint('fk_room_types_reviewed_by', 'room_types', type_='foreignkey')
    op.drop_index(op.f('ix_room_types_status'), table_name='room_types')
    op.drop_index(op.f('ix_room_types_reviewed_by'), table_name='room_types')
    op.drop_column('room_types', 'version')
    op.drop_column('room_types', 'reviewed_at')
    op.drop_column('room_types', 'reviewed_by')
    op.drop_column('room_types', 'review_notes')
    op.drop_column('room_types', 'meal_add_on_options')
    op.drop_column('room_types', 'extra_bed_rules')
    op.drop_column('room_types', 'status')

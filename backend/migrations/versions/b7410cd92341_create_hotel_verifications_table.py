"""create hotel verifications table and add partner_id to hotels

Revision ID: b7410cd92341
Revises: c8230da46721
Create Date: 2026-08-31 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7410cd92341'
down_revision: Union[str, Sequence[str], None] = 'c8230da46721'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add partner_id to hotels table
    op.add_column(
        'hotels',
        sa.Column('partner_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_hotels_partner_id_users',
        'hotels',
        'users',
        ['partner_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(op.f('ix_hotels_partner_id'), 'hotels', ['partner_id'], unique=False)

    # 2. Create hotel_verifications table
    op.create_table(
        'hotel_verifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('hotel_id', sa.Integer(), nullable=False),
        sa.Column('business_name', sa.String(length=150), nullable=False),
        sa.Column('business_type', sa.String(length=50), server_default='PROPRIETORSHIP', nullable=False),
        sa.Column('gstin', sa.String(length=15), nullable=True),
        sa.Column('pan', sa.String(length=10), nullable=True),
        sa.Column('bank_account_number', sa.String(length=50), nullable=True),
        sa.Column('bank_ifsc', sa.String(length=11), nullable=True),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('bank_beneficiary_name', sa.String(length=150), nullable=True),
        sa.Column('document_proof_type', sa.String(length=50), nullable=True),
        sa.Column('document_proof_url', sa.String(length=2048), nullable=True),
        sa.Column('verification_status', sa.String(length=30), server_default='PENDING', nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('admin_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['hotel_id'], ['hotels.id'], name='fk_hotel_verifications_hotel_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], name='fk_hotel_verifications_reviewed_by_users', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hotel_id', name='uq_hotel_verifications_hotel_id'),
    )
    op.create_index(op.f('ix_hotel_verifications_hotel_id'), 'hotel_verifications', ['hotel_id'], unique=True)
    op.create_index(op.f('ix_hotel_verifications_reviewed_by'), 'hotel_verifications', ['reviewed_by'], unique=False)
    op.create_index('ix_hotel_verifications_status', 'hotel_verifications', ['verification_status'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_hotel_verifications_status', table_name='hotel_verifications')
    op.drop_index(op.f('ix_hotel_verifications_reviewed_by'), table_name='hotel_verifications')
    op.drop_index(op.f('ix_hotel_verifications_hotel_id'), table_name='hotel_verifications')
    op.drop_table('hotel_verifications')

    op.drop_constraint('fk_hotels_partner_id_users', 'hotels', type_='foreignkey')
    op.drop_index(op.f('ix_hotels_partner_id'), table_name='hotels')
    op.drop_column('hotels', 'partner_id')

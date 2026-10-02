"""productionize hotel payouts

Revision ID: f7a3d9c2e5b1
Revises: f2c8a4d6e1b9
"""

from alembic import op
import sqlalchemy as sa


revision = "f7a3d9c2e5b1"
down_revision = "f2c8a4d6e1b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("settlements", "status", existing_type=sa.String(10), type_=sa.String(23), existing_nullable=False)
    op.alter_column("settlement_events", "old_status", existing_type=sa.String(10), type_=sa.String(23), existing_nullable=True)
    op.alter_column("settlement_events", "new_status", existing_type=sa.String(10), type_=sa.String(23), existing_nullable=False)
    op.add_column("payouts", sa.Column("destination_fingerprint", sa.String(64), nullable=True))
    op.add_column("payouts", sa.Column("provider_contact_id", sa.String(120), nullable=True))
    op.add_column("payouts", sa.Column("provider_fund_account_id", sa.String(120), nullable=True))
    op.add_column("payouts", sa.Column("provider_utr", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("payouts", "provider_utr")
    op.drop_column("payouts", "provider_fund_account_id")
    op.drop_column("payouts", "provider_contact_id")
    op.drop_column("payouts", "destination_fingerprint")
    op.alter_column("settlement_events", "new_status", existing_type=sa.String(23), type_=sa.String(10), existing_nullable=False)
    op.alter_column("settlement_events", "old_status", existing_type=sa.String(23), type_=sa.String(10), existing_nullable=True)
    op.alter_column("settlements", "status", existing_type=sa.String(23), type_=sa.String(10), existing_nullable=False)

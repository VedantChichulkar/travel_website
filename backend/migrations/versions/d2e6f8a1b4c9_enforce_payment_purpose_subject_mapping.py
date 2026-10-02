"""enforce payment purpose subject mapping

Revision ID: d2e6f8a1b4c9
Revises: be91d4f6a2c7
"""
from alembic import op


revision = "d2e6f8a1b4c9"
down_revision = "be91d4f6a2c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_payments_single_subject", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_single_subject",
        "payments",
        "(purpose = 'BOOKING' AND booking_id IS NOT NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR "
        "(purpose = 'VERIFICATION_FEE' AND booking_id IS NULL AND verification_hotel_id IS NOT NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR "
        "(purpose = 'ADVERTISING_CAMPAIGN' AND booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NOT NULL AND safari_request_id IS NULL) OR "
        "(purpose = 'SAFARI_BOOKING' AND booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_payments_single_subject", "payments", type_="check")
    op.create_check_constraint(
        "ck_payments_single_subject",
        "payments",
        "(booking_id IS NOT NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR "
        "(booking_id IS NULL AND verification_hotel_id IS NOT NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NULL) OR "
        "(booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NOT NULL AND safari_request_id IS NULL) OR "
        "(booking_id IS NULL AND verification_hotel_id IS NULL AND advertising_campaign_id IS NULL AND safari_request_id IS NOT NULL)",
    )

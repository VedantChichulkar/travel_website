from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.booking import BookingStatus, CancellationStatus, CancellationType, PaymentReconciliationStatus, PaymentStatus, RefundStatus
from app.models.settlement import PayoutStatus, SettlementAdjustmentKind, SettlementStatus


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SettlementBookingSummary(OrmModel):
    id: int
    booking_reference: str
    checked_out_at: datetime | None
    check_in: date
    check_out: date
    status: BookingStatus
    payment_status: PaymentStatus
    policy_snapshot: dict[str, object]
    payments: list["SettlementPaymentSummary"] = []
    cancellation: "SettlementCancellationSummary | None" = None


class SettlementPaymentSummary(OrmModel):
    id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    reconciliation_status: PaymentReconciliationStatus


class SettlementRefundSummary(OrmModel):
    id: int
    amount: Decimal
    status: RefundStatus


class SettlementCancellationSummary(OrmModel):
    id: int
    cancellation_type: CancellationType
    status: CancellationStatus
    refundable_amount: Decimal
    refunded_amount: Decimal
    requires_manual_review: bool
    refunds: list[SettlementRefundSummary] = []


class SettlementHotelSummary(OrmModel):
    id: int
    name: str


class SettlementAdjustmentResponse(OrmModel):
    id: int
    kind: SettlementAdjustmentKind
    amount: Decimal
    reason: str
    applies_to_current_settlement: bool
    applied_to_settlement_id: int | None
    applied_at: datetime | None
    created_by_user_id: int
    created_at: datetime


class SettlementEventResponse(OrmModel):
    id: int
    old_status: SettlementStatus | None
    new_status: SettlementStatus
    note: str
    actor_user_id: int | None
    created_at: datetime


class PayoutResponse(OrmModel):
    id: int
    provider: str
    provider_payout_id: str | None
    provider_status: str | None
    provider_utr: str | None
    status: PayoutStatus
    amount: Decimal
    currency: str
    attempts: int
    failure_reason: str | None
    reconciliation_reason: str | None
    initiated_at: datetime | None
    completed_at: datetime | None


class SettlementResponse(OrmModel):
    id: int
    hotel_id: int
    booking_id: int
    currency: str
    gross_amount: Decimal
    commission_rate: Decimal | None
    commission_rule: str | None
    vayora_fee: Decimal
    refund_deductions: Decimal
    adjustment_total: Decimal
    net_payable: Decimal
    eligibility_date: datetime
    status: SettlementStatus
    hold_reason: str | None
    payout_provider: str | None
    payout_provider_reference: str | None
    processing_at: datetime | None
    settled_at: datetime | None
    created_at: datetime
    booking: SettlementBookingSummary
    hotel: SettlementHotelSummary
    adjustments: list[SettlementAdjustmentResponse]
    events: list[SettlementEventResponse]
    payout: PayoutResponse | None


class PartnerPayoutResponse(OrmModel):
    status: PayoutStatus
    amount: Decimal
    currency: str
    provider_utr: str | None
    failure_reason: str | None
    reconciliation_reason: str | None
    initiated_at: datetime | None
    completed_at: datetime | None


class PartnerSettlementResponse(OrmModel):
    id: int
    hotel_id: int
    booking_id: int
    currency: str
    gross_amount: Decimal
    commission_rate: Decimal | None
    commission_rule: str | None
    vayora_fee: Decimal
    refund_deductions: Decimal
    adjustment_total: Decimal
    net_payable: Decimal
    eligibility_date: datetime
    status: SettlementStatus
    hold_reason: str | None
    processing_at: datetime | None
    settled_at: datetime | None
    created_at: datetime
    booking: SettlementBookingSummary
    hotel: SettlementHotelSummary
    adjustments: list[SettlementAdjustmentResponse]
    events: list[SettlementEventResponse]
    payout: PartnerPayoutResponse | None


class SettlementHoldRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class SettlementProcessingRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class SettlementAdjustmentRequest(BaseModel):
    kind: SettlementAdjustmentKind
    amount: Decimal
    reason: str = Field(min_length=5, max_length=1000)

    @model_validator(mode="after")
    def nonzero(self):
        if self.amount == 0:
            raise ValueError("amount cannot be zero")
        return self

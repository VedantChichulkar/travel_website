from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.booking import PaymentReconciliationStatus, PaymentStatus, RefundStatus
from app.models.safari import SafariDocumentKind, SafariRequestStatus


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SafariPublic(OrmModel):
    id: int; name: str; slug: str; short_description: str
    district_id: int | None; destination_id: int | None
    district_name: str | None = None; district_slug: str | None = None
    destination_name: str | None = None; destination_slug: str | None = None
    destination_path: str | None = None; hotel_destination_filter: str | None = None
    booking_categories: list[dict[str, object]]; vehicle_options: list[dict[str, object]]
    shifts: list[str]; zones: list[str]; gates: list[str]
    traveller_requirements: dict[str, object]
    official_reference_required: bool; official_contact_required: bool; official_document_required: bool
    source_url: str | None; last_verified_at: datetime | None
    operational_notices: list["SafariOperationalNoticeResponse"] = Field(default_factory=list)


class SafariOperationalNoticeResponse(OrmModel):
    id: int; safari_id: int | None; title: str; body: str; severity: str
    effective_from: datetime | None; effective_until: datetime | None; is_active: bool
    source_url: str | None; last_verified_at: datetime | None; created_at: datetime; updated_at: datetime


class AvailabilityRequestCreate(BaseModel):
    preferred_date: date
    preferred_shift: str | None = Field(default=None, max_length=100)
    preferred_booking_category: str | None = Field(default=None, max_length=100)
    preferred_vehicle_option: str | None = Field(default=None, max_length=100)
    visitor_count: int = Field(ge=1, le=20)
    alternate_preference: str | None = Field(default=None, max_length=500)


class AlternativeInput(BaseModel):
    safari_date: date
    shift: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=160)
    gate: str | None = Field(default=None, max_length=160)
    booking_category: str | None = Field(default=None, max_length=100)
    vehicle_option: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=500)


class AlternativeResponse(OrmModel):
    id: int; safari_date: date; shift: str | None; zone: str | None; gate: str | None
    booking_category: str | None; vehicle_option: str | None; note: str | None


class SafariDocumentResponse(OrmModel):
    id: int; kind: SafariDocumentKind; document_type: str; original_name: str; content_type: str; size: int; created_at: datetime


class TravellerResponse(BaseModel):
    id: int; position: int; details: dict[str, Any]; documents: list[SafariDocumentResponse]


class SafariRequestResponse(BaseModel):
    id: int; request_reference: str; safari: SafariPublic; preferred_date: date; preferred_shift: str | None
    preferred_booking_category: str | None; preferred_vehicle_option: str | None
    visitor_count: int; alternate_preference: str | None; status: SafariRequestStatus; availability_result: str | None
    alternatives: list[AlternativeResponse]; selected_alternative_id: int | None
    target_response_at: datetime; responded_at: datetime | None; overdue: bool
    payable_amount: Decimal | None; currency: str | None; price_breakdown: dict[str, object] | None
    payment_status: PaymentStatus; payment_reconciliation_status: PaymentReconciliationStatus | None
    refund_status: RefundStatus | None
    travellers: list[TravellerResponse]; confirmation_documents: list[SafariDocumentResponse]
    external_booking_reference: str | None; confirmed_date: date | None; confirmed_shift: str | None
    confirmed_zone: str | None; confirmed_gate: str | None; reporting_instructions: str | None
    confirmed_booking_category: str | None; confirmed_vehicle_option: str | None
    official_booking_contact_masked: str | None; operator_confirmed_at: datetime | None
    final_amount: Decimal | None; failure_reason: str | None; created_at: datetime; updated_at: datetime


class AvailabilityDecision(BaseModel):
    action: Literal["START_CHECK", "MARK_AVAILABLE", "MARK_UNAVAILABLE"]
    reason: str = Field(min_length=2, max_length=2000)
    alternatives: list[AlternativeInput] = Field(default_factory=list, max_length=10)
    internal_notes: str | None = Field(default=None, max_length=4000)


class AlternativeSelection(BaseModel):
    alternative_id: int


class TravellerInput(BaseModel):
    details: dict[str, Any]


class TravellerSubmission(BaseModel):
    travellers: list[TravellerInput] = Field(min_length=1, max_length=20)


class PricingInput(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    breakdown: dict[str, object]
    reason: str = Field(min_length=2, max_length=2000)


class ConfirmationInput(BaseModel):
    booking_reference: str | None = Field(default=None, min_length=2, max_length=160)
    safari_date: date
    shift: str | None = Field(default=None, max_length=100)
    zone: str | None = Field(default=None, max_length=160)
    gate: str | None = Field(default=None, max_length=160)
    booking_category: str | None = Field(default=None, max_length=100)
    vehicle_option: str | None = Field(default=None, max_length=100)
    official_booking_contact: str | None = Field(default=None, min_length=4, max_length=160)
    reporting_instructions: str = Field(min_length=2, max_length=4000)
    final_amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=2, max_length=2000)


class BookingFailureInput(BaseModel):
    reason: str = Field(min_length=2, max_length=2000)


class SafariQueueFilter(BaseModel):
    status: SafariRequestStatus | None = None
    overdue_only: bool = False


class SafariConfigurationUpdate(BaseModel):
    booking_categories: list[dict[str, object]] | None = None
    vehicle_options: list[dict[str, object]] | None = None
    shifts: list[str] | None = None; zones: list[str] | None = None; gates: list[str] | None = None
    traveller_requirements: dict[str, object] | None = None
    official_reference_required: bool | None = None
    official_contact_required: bool | None = None
    official_document_required: bool | None = None
    source_url: str | None = Field(default=None, max_length=2048)
    last_verified_at: datetime | None = None
    reason: str = Field(min_length=2, max_length=2000)


class SafariOperationalNoticeCreate(BaseModel):
    safari_id: int | None = None
    title: str = Field(min_length=2, max_length=200); body: str = Field(min_length=2, max_length=5000)
    severity: Literal["INFO", "WARNING", "RESTRICTION"] = "INFO"
    effective_from: datetime | None = None; effective_until: datetime | None = None
    is_active: bool = True; source_url: str | None = Field(default=None, max_length=2048)
    last_verified_at: datetime | None = None; reason: str = Field(min_length=2, max_length=2000)

    @model_validator(mode="after")
    def valid_window(self):
        if self.effective_from and self.effective_until and self.effective_until <= self.effective_from:
            raise ValueError("effective_until must be after effective_from")
        return self


class SafariOperationalNoticeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200); body: str | None = Field(default=None, min_length=2, max_length=5000)
    severity: Literal["INFO", "WARNING", "RESTRICTION"] | None = None
    effective_from: datetime | None = None; effective_until: datetime | None = None
    is_active: bool | None = None; source_url: str | None = Field(default=None, max_length=2048)
    last_verified_at: datetime | None = None; reason: str = Field(min_length=2, max_length=2000)

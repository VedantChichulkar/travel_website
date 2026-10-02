import re
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.core.sensitive_data import mask_tail

from app.models.hotel_verification import BusinessType, VerificationStatus
from app.models.booking import PaymentStatus, RefundStatus
from app.schemas.hotel import HotelResponse


GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class VerificationSubmitRequest(BaseModel):
    business_name: str = Field(min_length=2, max_length=150)
    business_type: BusinessType = Field(default=BusinessType.PROPRIETORSHIP)
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)
    bank_account_number: str | None = Field(default=None, min_length=8, max_length=30)
    bank_ifsc: str | None = Field(default=None, max_length=11)
    bank_name: str | None = Field(default=None, min_length=2, max_length=100)
    bank_beneficiary_name: str | None = Field(default=None, min_length=2, max_length=150)
    document_proof_type: str | None = Field(default=None, max_length=50)
    document_reference: str | None = Field(default=None, max_length=512)

    @field_validator("business_name")
    @classmethod
    def normalize_business_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("business_name must contain at least 2 characters")
        return normalized

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().upper()
        if not GSTIN_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid GSTIN format. Example: 27ABCDE1234F1Z5")
        return normalized

    @field_validator("pan")
    @classmethod
    def validate_pan(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().upper()
        if not PAN_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid PAN format. Example: ABCDE1234F")
        return normalized

    @field_validator("bank_ifsc")
    @classmethod
    def validate_ifsc(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().upper()
        if not IFSC_PATTERN.fullmatch(normalized):
            raise ValueError("Invalid IFSC code format. Example: HDFC0001234")
        return normalized

    @field_validator("bank_account_number")
    @classmethod
    def validate_bank_account(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = re.sub(r"[\s-]", "", value)
        if not re.fullmatch(r"^\d{8,30}$", normalized):
            raise ValueError("bank_account_number must contain 8 to 30 digits")
        return normalized


class ReviewActionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_INFO = "REQUEST_INFO"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class VerificationReviewRequest(BaseModel):
    action: ReviewActionType
    rejection_reason: str | None = Field(default=None, max_length=1000)
    admin_notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_action_fields(self) -> Self:
        if self.action == ReviewActionType.REJECT and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting a verification")
        if self.action in (ReviewActionType.REQUEST_INFO, ReviewActionType.REQUEST_CHANGES) and not self.admin_notes:
            raise ValueError("admin_notes are required when requesting additional information")
        return self


class VerificationFeeStatusResponse(BaseModel):
    amount: Decimal
    currency: str
    payment_status: PaymentStatus
    payment_id: int | None = None
    provider_order_id: str | None = None
    payment_reference: str | None = None
    paid_at: datetime | None = None
    refund_status: RefundStatus | None = None
    refund_id: int | None = None
    refund_reference: str | None = None
    refund_failure_reason: str | None = None
    disclaimer: str = "Payment of the verification processing fee does not guarantee approval. Only an Admin decision can verify a hotel."


class HotelVerificationResponse(OrmModel):
    id: int
    hotel_id: int
    business_name: str
    business_type: BusinessType
    gstin: str | None
    pan: str | None
    bank_account_number: str | None
    bank_ifsc: str | None
    bank_name: str | None
    bank_beneficiary_name: str | None
    document_proof_type: str | None
    document_available: bool
    document_original_name: str | None
    document_content_type: str | None
    document_size: int | None
    document_uploaded_at: datetime | None
    verification_status: VerificationStatus
    rejection_reason: str | None
    admin_notes: str | None
    reviewed_by: int | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    fee: VerificationFeeStatusResponse | None = None

    @field_serializer("gstin", "pan", "bank_account_number", "bank_ifsc")
    def serialize_sensitive(self, value: str | None) -> str | None:
        return mask_tail(value)


class PrivateDocumentUploadResponse(BaseModel):
    document_reference: str
    original_name: str
    content_type: str
    size: int


class AdminVerificationListItem(OrmModel):
    id: int
    hotel_id: int
    hotel_name: str
    hotel_slug: str
    hotel_city: str
    hotel_state: str
    partner_id: int | None
    partner_name: str | None
    partner_email: str | None
    business_name: str
    business_type: BusinessType
    verification_status: VerificationStatus
    payment_status: PaymentStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime


class AdminVerificationDetailResponse(OrmModel):
    verification: HotelVerificationResponse
    hotel: HotelResponse
    partner: dict | None = None


class PartnerHotelOverviewResponse(BaseModel):
    hotel: HotelResponse | None
    verification: HotelVerificationResponse | None
    has_hotel: bool
    is_onboarding_complete: bool
    can_access_portal: bool
    verification_fee: VerificationFeeStatusResponse | None = None

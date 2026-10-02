from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.support import SupportEnquiryType


class PublicContactConfig(BaseModel):
    email: str | None
    whatsapp_url: str | None


class SupportEnquiryCreate(BaseModel):
    idempotency_key: str = Field(min_length=16, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    enquiry_type: SupportEnquiryType
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mobile: str = Field(min_length=8, max_length=16, pattern=r"^\+?[1-9]\d{7,14}$")
    message: str = Field(min_length=10, max_length=5000)
    customer_reference: str | None = Field(default=None, min_length=3, max_length=64)
    property_name: str | None = Field(default=None, min_length=2, max_length=160)
    location: str | None = Field(default=None, min_length=2, max_length=160)

    @model_validator(mode="after")
    def validate_context(self):
        if self.enquiry_type in {
            SupportEnquiryType.BOOKING_HELP,
            SupportEnquiryType.SAFARI_HELP,
            SupportEnquiryType.CANCELLATION_REFUND,
        } and not self.customer_reference:
            raise ValueError("A customer-facing booking or Safari reference is required")
        if self.enquiry_type == SupportEnquiryType.HOTEL_PARTNER and not self.property_name:
            raise ValueError("Property or business name is required")
        return self


class SupportEnquiryReceipt(BaseModel):
    reference: str
    enquiry_type: SupportEnquiryType
    created_at: datetime
    next_step: str


class AdminSupportEnquiry(BaseModel):
    reference: str
    enquiry_type: SupportEnquiryType
    status: str
    name: str
    email: str
    mobile: str
    message: str
    customer_reference: str | None
    property_name: str | None
    location: str | None
    created_at: datetime


class AdminSupportEnquiryList(BaseModel):
    items: list[AdminSupportEnquiry]
    total: int

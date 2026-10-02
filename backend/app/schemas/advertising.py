from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.advertising import AdvertiserStatus, AdvertiserType, AdvertisingCampaignStatus, AdvertisingPlacement
from app.models.booking import PaymentStatus

class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AdvertisingPlan(BaseModel):
    code: str
    name: str
    placement: AdvertisingPlacement
    amount: Decimal
    currency: str
    duration_days: int


class AdvertisingConfigResponse(BaseModel):
    plans: list[AdvertisingPlan]
    rotation_seconds: int


class CampaignCreate(BaseModel):
    plan_code: str = Field(min_length=1, max_length=80)
    start_at: datetime
    district_slug: str | None = Field(default=None, max_length=140)
    destination_slug: str | None = Field(default=None, max_length=160)
    alt_text: str | None = Field(default=None, max_length=255)


class AdvertiserProfileUpsert(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    contact_person: str = Field(min_length=2, max_length=100)
    business_email: EmailStr
    phone: str = Field(min_length=8, max_length=16, pattern=r"^\+[1-9]\d{7,14}$")
    category: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    website: str | None = Field(default=None, max_length=2048)

    @field_validator("business_name", "contact_person", "category")
    @classmethod
    def normalize_required(cls, value: str) -> str:
        return " ".join(value.split())


class AdvertiserProfileResponse(OrmModel):
    id: int
    public_id: str
    business_name: str
    contact_person: str
    business_email: EmailStr
    phone: str
    category: str
    description: str | None
    website: str | None
    status: AdvertiserStatus
    suspended_reason: str | None
    created_at: datetime
    updated_at: datetime


class ExternalCampaignCreate(BaseModel):
    campaign_name: str = Field(min_length=2, max_length=160)
    headline: str = Field(min_length=2, max_length=120)
    short_copy: str = Field(min_length=2, max_length=280)
    target_url: str = Field(min_length=8, max_length=2048)
    plan_code: str = Field(min_length=1, max_length=80)
    start_at: datetime
    district_slug: str | None = Field(default=None, max_length=140)
    destination_slug: str | None = Field(default=None, max_length=160)
    alt_text: str | None = Field(default=None, max_length=255)
    creative_rights_confirmed: bool
    creative_source: str | None = Field(default=None, max_length=255)


class ExternalCampaignUpdate(BaseModel):
    campaign_name: str | None = Field(default=None, min_length=2, max_length=160)
    headline: str | None = Field(default=None, min_length=2, max_length=120)
    short_copy: str | None = Field(default=None, min_length=2, max_length=280)
    target_url: str | None = Field(default=None, min_length=8, max_length=2048)
    alt_text: str | None = Field(default=None, max_length=255)
    creative_rights_confirmed: bool | None = None
    creative_source: str | None = Field(default=None, max_length=255)
    version: int = Field(ge=1)


class CampaignResponse(OrmModel):
    id: int
    public_id: str
    advertiser_type: AdvertiserType = AdvertiserType.HOTEL
    advertiser_profile_id: int | None = None
    advertiser_name: str | None = None
    advertiser_status: AdvertiserStatus | None = None
    hotel_id: int | None
    hotel_name: str | None = None
    campaign_name: str | None = None
    headline: str | None = None
    short_copy: str | None = None
    target_url: str | None = None
    placement: AdvertisingPlacement
    plan_code: str
    district_id: int | None
    destination_id: int | None
    district_name: str | None = None
    destination_name: str | None = None
    creative_url: str | None
    alt_text: str | None
    status: AdvertisingCampaignStatus
    start_at: datetime
    end_at: datetime
    price_amount: Decimal
    currency: str
    payment_status: PaymentStatus
    payment_reference: str | None = None
    review_reason: str | None
    refund_review_required: bool = False
    creative_rights_confirmed: bool = False
    creative_source: str | None = None
    version: int = 1
    impressions: int = 0
    clicks: int = 0
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime


class CampaignReviewRequest(BaseModel):
    action: Literal["APPROVE", "REQUEST_CHANGES", "REJECT", "PAUSE"]
    reason: str | None = Field(default=None, max_length=2000)


class PublicCampaign(BaseModel):
    id: str
    placement: AdvertisingPlacement
    creative_url: str
    alt_text: str
    sponsor_label: str = "Sponsored"
    advertiser_name: str
    headline: str | None = None
    short_copy: str | None = None
    advertiser_type: AdvertiserType
    is_external: bool = False
    destination_url: str


class PublicCampaignList(BaseModel):
    items: list[PublicCampaign]
    rotation_seconds: int


class AdvertisingEventRequest(BaseModel):
    event_id: str = Field(min_length=8, max_length=100)


class AdvertisingEventResponse(BaseModel):
    recorded: bool


class AdvertiserSuspendRequest(BaseModel):
    suspended: bool
    reason: str = Field(min_length=2, max_length=2000)

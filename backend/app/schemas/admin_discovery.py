from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.place import SpiritualTradition


LifecycleStatus = Literal["DRAFT", "PUBLISHED", "UNPUBLISHED"]


class FAQInput(BaseModel):
    id: int | None = None
    question: str = Field(min_length=3, max_length=500)
    answer: str = Field(min_length=1, max_length=10_000)
    display_order: int = Field(default=0, ge=0, le=100_000)
    is_active: bool = True

    @field_validator("question", "answer")
    @classmethod
    def clean_faq_text(cls, value: str) -> str:
        return value.strip()


class DistrictOption(BaseModel):
    id: int
    name: str
    slug: str
    division: str


class InterestOption(BaseModel):
    id: int
    name: str
    slug: str
    display_order: int


class DiscoveryReferenceData(BaseModel):
    districts: list[DistrictOption]
    interests: list[InterestOption]
    spiritual_traditions: list[SpiritualTradition]


class DestinationInput(BaseModel):
    district_id: int
    name: str = Field(min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=20_000)
    short_summary: str | None = Field(default=None, max_length=500)
    faqs: list[FAQInput] = Field(default_factory=list, max_length=50)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()


class DestinationCreate(DestinationInput):
    pass


class DestinationUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=20_000)
    short_summary: str | None = Field(default=None, max_length=500)
    faqs: list[FAQInput] | None = Field(default=None, max_length=50)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value


class PlaceInput(BaseModel):
    district_id: int
    destination_id: int | None = None
    name: str = Field(min_length=2, max_length=160)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20_000)
    interest_ids: list[int] = Field(default_factory=list, max_length=9)
    spiritual_tradition: SpiritualTradition | None = None
    is_featured: bool = False
    display_order: int = Field(default=0, ge=0, le=100_000)
    address: str | None = Field(default=None, max_length=500)
    opening_hours: str | None = Field(default=None, max_length=5_000)
    entry_fee_info: str | None = Field(default=None, max_length=5_000)
    recommended_visit_duration: str | None = Field(default=None, max_length=120)
    best_time_to_visit: str | None = Field(default=None, max_length=300)
    getting_there: str | None = Field(default=None, max_length=10_000)
    nearest_railway_station: str | None = Field(default=None, max_length=300)
    nearest_airport: str | None = Field(default=None, max_length=300)
    visitor_info_source: str | None = Field(default=None, max_length=500)
    visitor_info_source_url: str | None = Field(default=None, max_length=2048)
    visitor_info_verified_at: date | None = None
    faqs: list[FAQInput] = Field(default_factory=list, max_length=50)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("interest_ids")
    @classmethod
    def unique_interests(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("Duplicate interests are not allowed")
        return value


class PlaceCreate(PlaceInput):
    pass


class PlaceUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    district_id: int | None = None
    destination_id: int | None = None
    name: str | None = Field(default=None, min_length=2, max_length=160)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20_000)
    interest_ids: list[int] | None = Field(default=None, max_length=9)
    spiritual_tradition: SpiritualTradition | None = None
    is_featured: bool | None = None
    display_order: int | None = Field(default=None, ge=0, le=100_000)
    address: str | None = Field(default=None, max_length=500)
    opening_hours: str | None = Field(default=None, max_length=5_000)
    entry_fee_info: str | None = Field(default=None, max_length=5_000)
    recommended_visit_duration: str | None = Field(default=None, max_length=120)
    best_time_to_visit: str | None = Field(default=None, max_length=300)
    getting_there: str | None = Field(default=None, max_length=10_000)
    nearest_railway_station: str | None = Field(default=None, max_length=300)
    nearest_airport: str | None = Field(default=None, max_length=300)
    visitor_info_source: str | None = Field(default=None, max_length=500)
    visitor_info_source_url: str | None = Field(default=None, max_length=2048)
    visitor_info_verified_at: date | None = None
    faqs: list[FAQInput] | None = Field(default=None, max_length=50)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else value

    @field_validator("interest_ids")
    @classmethod
    def unique_interests(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(value) != len(set(value)):
            raise ValueError("Duplicate interests are not allowed")
        return value


class LifecycleAction(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=1000)


class AdminInterestRead(BaseModel):
    id: int
    name: str
    slug: str


class AdminFAQRead(FAQInput):
    id: int


class AdminEntityMediaRead(BaseModel):
    id: int
    media_asset_id: int
    role: Literal["HERO", "GALLERY"]
    display_order: int
    public_url: str
    alt_text: str
    specificity: str
    status: str
    creator_owner: str
    source_name: str
    source_url: str | None
    usage_basis: str
    attribution_text: str | None
    rights_verified_at: date


class AdminDestinationRead(BaseModel):
    id: int
    district_id: int
    district_name: str
    district_slug: str
    name: str
    slug: str
    description: str | None
    short_summary: str | None
    image_url: str | None
    image_alt: str | None
    media_asset_id: int | None
    status: LifecycleStatus
    content_source: str
    admin_overridden: bool
    version: int
    public_path: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    faqs: list[AdminFAQRead]
    media: list[AdminEntityMediaRead]


class AdminPlaceRead(BaseModel):
    id: int
    district_id: int
    district_name: str
    district_slug: str
    destination_id: int | None
    destination_name: str | None
    name: str
    slug: str
    short_description: str | None
    description: str | None
    address: str | None
    opening_hours: str | None
    entry_fee_info: str | None
    recommended_visit_duration: str | None
    best_time_to_visit: str | None
    getting_there: str | None
    nearest_railway_station: str | None
    nearest_airport: str | None
    visitor_info_source: str | None
    visitor_info_source_url: str | None
    visitor_info_verified_at: date | None
    image_url: str | None
    image_alt: str | None
    media_asset_id: int | None
    interests: list[AdminInterestRead]
    spiritual_tradition: SpiritualTradition | None
    is_featured: bool
    display_order: int
    status: LifecycleStatus
    content_source: str
    admin_overridden: bool
    version: int
    public_path: str
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    faqs: list[AdminFAQRead]
    media: list[AdminEntityMediaRead]


class MediaUpdate(BaseModel):
    expected_version: int = Field(ge=1)
    role: Literal["HERO", "GALLERY"]
    display_order: int = Field(ge=0, le=100_000)
    alt_text: str = Field(min_length=5, max_length=300)


class AdminDestinationList(BaseModel):
    items: list[AdminDestinationRead]
    total: int


class AdminPlaceList(BaseModel):
    items: list[AdminPlaceRead]
    total: int


class PublicationImpact(BaseModel):
    entity: AdminDestinationRead | AdminPlaceRead
    affected: dict[str, int] = Field(default_factory=dict)


class PublicMediaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    entity_type: str
    entity_id: int
    public_url: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    alt_text: str
    specificity: str
    creator_owner: str
    source_name: str
    source_url: str | None
    usage_basis: str
    attribution_text: str | None
    rights_verified_at: date
    status: str
    replaced_by_asset_id: int | None
    created_at: datetime

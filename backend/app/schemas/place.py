from datetime import date

from pydantic import BaseModel

from app.models.place import SpiritualTradition


class PublicInterestSummary(BaseModel):
    name: str
    slug: str
    description: str | None
    display_order: int
    path: str


class PublicInterestList(BaseModel):
    items: list[PublicInterestSummary]
    total: int


class PublicPlaceLocation(BaseModel):
    name: str
    slug: str
    path: str


class PublicFAQ(BaseModel):
    id: int
    question: str
    answer: str
    display_order: int


class PublicDiscoveryMedia(BaseModel):
    id: int
    media_asset_id: int
    public_url: str
    alt_text: str
    specificity: str
    role: str
    display_order: int
    attribution_text: str | None
    source_name: str


class PublicPlaceSummary(BaseModel):
    name: str
    slug: str
    short_description: str | None
    image_url: str | None
    image_alt: str | None
    image_status: str | None
    is_featured: bool
    district: PublicPlaceLocation
    destination: PublicPlaceLocation | None
    interests: list[PublicInterestSummary]
    path: str


class PublicPlaceDetail(PublicPlaceSummary):
    description: str | None
    spiritual_tradition: SpiritualTradition | None
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
    gallery: list[PublicDiscoveryMedia]
    faqs: list[PublicFAQ]
    related_places: list[PublicPlaceSummary]


class PublicPlaceList(BaseModel):
    items: list[PublicPlaceSummary]
    total: int
    limit: int
    offset: int

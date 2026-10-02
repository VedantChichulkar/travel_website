from typing import Literal

from pydantic import BaseModel

from app.schemas.place import PublicDiscoveryMedia, PublicFAQ, PublicPlaceSummary


class PublicDestinationSummary(BaseModel):
    name: str
    slug: str
    description: str | None
    short_summary: str | None
    image_url: str | None
    image_alt: str | None
    image_status: str | None
    district_name: str
    district_slug: str
    path: str


class PublicDestinationDetail(PublicDestinationSummary):
    gallery: list[PublicDiscoveryMedia]
    faqs: list[PublicFAQ]
    places: list[PublicPlaceSummary]


class PublicDistrictSummary(BaseModel):
    name: str
    slug: str
    division: str
    short_description: str | None
    hero_image_url: str | None
    path: str


class PublicDistrictDetail(PublicDistrictSummary):
    destinations: list[PublicDestinationSummary]


class PublicDistrictList(BaseModel):
    items: list[PublicDistrictSummary]
    total: int


class PublicDestinationList(BaseModel):
    items: list[PublicDestinationSummary]
    total: int


class DestinationSearchResult(BaseModel):
    kind: Literal["DISTRICT", "DESTINATION", "PLACE", "STORY"]
    name: str
    slug: str
    district_name: str | None = None
    district_slug: str | None = None
    destination_name: str | None = None
    destination_slug: str | None = None
    path: str


class DestinationSearchResponse(BaseModel):
    items: list[DestinationSearchResult]
    total: int

from pydantic import BaseModel

from app.schemas.place import PublicInterestSummary, PublicPlaceSummary


class PublicStoryDistrict(BaseModel):
    name: str
    slug: str
    path: str


class PublicStoryDestination(BaseModel):
    name: str
    slug: str
    district_name: str
    district_slug: str
    path: str


class PublicDiscoveryStorySummary(BaseModel):
    title: str
    slug: str
    short_description: str
    image_url: str | None
    is_featured: bool
    interests: list[PublicInterestSummary]
    districts: list[PublicStoryDistrict]
    path: str


class PublicDiscoveryStoryDetail(PublicDiscoveryStorySummary):
    body: str
    destinations: list[PublicStoryDestination]
    related_places: list[PublicPlaceSummary]


class PublicDiscoveryStoryList(BaseModel):
    items: list[PublicDiscoveryStorySummary]
    total: int

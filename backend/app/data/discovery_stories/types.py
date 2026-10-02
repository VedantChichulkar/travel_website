"""Typed records for Maharashtra Tourist Places' reviewed editorial discovery dataset."""

from dataclasses import dataclass

from app.data.provenance import SourceProvenance


@dataclass(frozen=True)
class DestinationReference:
    district_slug: str
    destination_slug: str


@dataclass(frozen=True)
class PlaceReference:
    district_slug: str
    place_slug: str


@dataclass(frozen=True)
class CuratedDiscoveryStory:
    title: str
    short_description: str
    body: str
    interest_slugs: tuple[str, ...]
    sources: tuple[SourceProvenance, ...]
    slug: str | None = None
    district_slugs: tuple[str, ...] = ()
    destination_references: tuple[DestinationReference, ...] = ()
    related_place_references: tuple[PlaceReference, ...] = ()
    image_url: str | None = None
    is_active: bool = True
    is_featured: bool = False
    display_order: int = 0

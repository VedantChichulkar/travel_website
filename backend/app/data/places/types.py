"""Typed records for Maharashtra Tourist Places' reviewed, operator-run Place dataset."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.provenance import SourceProvenance
from app.models.place import SpiritualTradition


@dataclass(frozen=True)
class CuratedPlace:
    name: str
    district_slug: str
    short_description: str
    description: str
    interest_slugs: tuple[str, ...]
    sources: tuple[SourceProvenance, ...]
    slug: str | None = None
    destination_slug: str | None = None
    spiritual_tradition: SpiritualTradition | str | None = None
    image_url: str | None = None
    is_active: bool = True
    is_featured: bool = False
    display_order: int = 0

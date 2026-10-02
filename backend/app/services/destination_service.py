from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.slug import unique_slug
from app.data.maharashtra import MAHARASHTRA_DISTRICTS_V1
from app.models.destination import Destination, District
from app.repositories import destination_repository as repository
from app.repositories import discovery_story_repository
from app.schemas.destination import (
    DestinationSearchResponse,
    DestinationSearchResult,
    PublicDestinationList,
    PublicDestinationDetail,
    PublicDestinationSummary,
    PublicDistrictDetail,
    PublicDistrictList,
    PublicDistrictSummary,
)
from app.schemas.place import PublicDiscoveryMedia, PublicFAQ
from app.services.place_service import _summary as _place_summary


@dataclass(frozen=True)
class HotelLocationFilter:
    district_ids: frozenset[int] = frozenset()
    district_names: frozenset[str] = frozenset()
    destination_ids: frozenset[int] = frozenset()
    destination_names: frozenset[str] = frozenset()


def seed_maharashtra_districts(db: Session) -> None:
    existing = set(db.scalars(select(District.slug)))
    for name, slug, division in MAHARASHTRA_DISTRICTS_V1:
        if slug not in existing:
            db.add(District(name=name, slug=slug, division=division, is_active=True))
            existing.add(slug)


def create_district(db: Session, *, name: str, division: str, is_active: bool = True) -> District:
    district = District(
        name=name.strip(),
        slug=unique_slug(db, District, name, max_length=140),
        division=division.strip(),
        is_active=is_active,
    )
    db.add(district)
    db.flush()
    return district


def create_destination(
    db: Session,
    *,
    district: District,
    name: str,
    description: str | None = None,
    image_url: str | None = None,
    is_active: bool = True,
) -> Destination:
    destination = Destination(
        district_id=district.id,
        name=name.strip(),
        slug=unique_slug(
            db,
            Destination,
            name,
            scope=(Destination.district_id == district.id,),
            max_length=160,
        ),
        description=description,
        image_url=image_url,
        is_active=is_active,
        published_at=datetime.now(timezone.utc) if is_active else None,
    )
    db.add(destination)
    db.flush()
    return destination


def _district(item: District) -> PublicDistrictSummary:
    return PublicDistrictSummary(
        name=item.name,
        slug=item.slug,
        division=item.division,
        short_description=item.short_description,
        hero_image_url=item.hero_image_url,
        path=f"/destinations/{item.slug}",
    )


def _destination(item: Destination) -> PublicDestinationSummary:
    return PublicDestinationSummary(
        name=item.name,
        slug=item.slug,
        description=item.description,
        short_summary=item.short_summary,
        image_url=item.image_url,
        image_alt=item.image_alt,
        image_status=item.media_asset.specificity if item.media_asset else None,
        district_name=item.district.name,
        district_slug=item.district.slug,
        path=f"/destinations/{item.district.slug}/{item.slug}",
    )


def list_districts(db: Session, query: str | None) -> PublicDistrictList:
    items = [_district(item) for item in repository.list_districts(db, query=query)]
    return PublicDistrictList(items=items, total=len(items))


def get_district(db: Session, slug: str) -> PublicDistrictDetail:
    district = repository.get_district_by_slug(db, slug)
    if district is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="District not found")
    destinations = [_destination(item) for item in repository.list_destinations(db, district.id)]
    return PublicDistrictDetail(**_district(district).model_dump(), destinations=destinations)


def list_destinations(db: Session, district_slug: str) -> PublicDestinationList:
    district = repository.get_district_by_slug(db, district_slug)
    if district is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="District not found")
    items = [_destination(item) for item in repository.list_destinations(db, district.id)]
    return PublicDestinationList(items=items, total=len(items))


def get_destination(db: Session, district_slug: str, destination_slug: str) -> PublicDestinationDetail:
    district = repository.get_district_by_slug(db, district_slug)
    destination = (
        repository.get_destination_by_identity(db, district.id, destination_slug) if district else None
    )
    if destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")
    summary = _destination(destination)
    gallery = [
        PublicDiscoveryMedia(
            id=value.id, media_asset_id=value.asset.id, public_url=value.asset.public_url,
            alt_text=value.asset.alt_text, specificity=value.asset.specificity, role=value.role,
            display_order=value.display_order, attribution_text=value.asset.attribution_text,
            source_name=value.asset.source_name,
        )
        for value in destination.media_items if value.role == "GALLERY" and value.asset.status == "ACTIVE"
    ]
    published_places = [
        value for value in destination.places
        if value.is_active and value.district.is_active and value.destination_id == destination.id
    ]
    published_places.sort(key=lambda value: (not value.is_featured, value.display_order, value.name))
    places = [_place_summary(value) for value in published_places]
    return PublicDestinationDetail(
        **summary.model_dump(), gallery=gallery,
        faqs=[PublicFAQ(id=value.id, question=value.question, answer=value.answer, display_order=value.display_order) for value in destination.faqs if value.is_active],
        places=places,
    )


def search(
    db: Session,
    query: str,
    limit: int,
    *,
    include_places: bool = False,
    include_stories: bool = False,
) -> DestinationSearchResponse:
    districts, destinations, places = repository.search(
        db, query, limit=limit, include_places=include_places
    )
    items = [
        DestinationSearchResult(kind="DISTRICT", name=item.name, slug=item.slug, path=f"/destinations/{item.slug}")
        for item in districts
    ]
    items.extend(
        DestinationSearchResult(
            kind="DESTINATION",
            name=item.name,
            slug=item.slug,
            district_name=item.district.name,
            district_slug=item.district.slug,
            path=f"/destinations/{item.district.slug}/{item.slug}",
        )
        for item in destinations
    )
    items.extend(
        DestinationSearchResult(
            kind="PLACE",
            name=item.name,
            slug=item.slug,
            district_name=item.district.name,
            district_slug=item.district.slug,
            destination_name=item.destination.name if item.destination else None,
            destination_slug=item.destination.slug if item.destination else None,
            path=f"/places/{item.district.slug}/{item.slug}",
        )
        for item in places
    )
    remaining = max(0, limit - len(items))
    if include_stories and remaining:
        stories = discovery_story_repository.search_stories(db, query, limit=remaining)
        items.extend(
            DestinationSearchResult(
                kind="STORY",
                name=item.title,
                slug=item.slug,
                path=f"/discover/{item.slug}",
            )
            for item in stories
        )
    return DestinationSearchResponse(items=items, total=len(items))


def resolve_hotel_location(db: Session, value: str) -> HotelLocationFilter:
    normalized = value.strip().strip("/")
    if "/" in normalized:
        district_value, destination_value = normalized.split("/", 1)
        district = repository.get_district_by_identity(db, district_value)
        destination = (
            repository.get_destination_by_identity(db, district.id, destination_value) if district else None
        )
        if destination is None:
            return HotelLocationFilter()
        return HotelLocationFilter(
            district_ids=frozenset({district.id}),
            district_names=frozenset({district.name.lower()}),
            destination_ids=frozenset({destination.id}),
            destination_names=frozenset({destination.name.lower()}),
        )

    district = repository.get_district_by_identity(db, normalized)
    if district:
        return HotelLocationFilter(
            district_ids=frozenset({district.id}), district_names=frozenset({district.name.lower()})
        )
    destinations = repository.find_destinations(db, normalized)
    return HotelLocationFilter(
        district_ids=frozenset(item.district_id for item in destinations),
        district_names=frozenset(item.district.name.lower() for item in destinations),
        destination_ids=frozenset(item.id for item in destinations),
        destination_names=frozenset(item.name.lower() for item in destinations),
    )

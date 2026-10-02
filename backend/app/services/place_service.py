from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.slug import unique_slug
from app.data.interests import MAHARASHTRA_INTERESTS_V1
from app.models.destination import Destination, District
from app.models.place import Interest, Place, SpiritualTradition
from app.repositories import place_repository as repository
from app.schemas.place import (
    PublicInterestList,
    PublicInterestSummary,
    PublicDiscoveryMedia,
    PublicFAQ,
    PublicPlaceDetail,
    PublicPlaceList,
    PublicPlaceLocation,
    PublicPlaceSummary,
)


def seed_interests(db: Session) -> None:
    existing = set(db.scalars(select(Interest.slug)))
    for name, slug, display_order in MAHARASHTRA_INTERESTS_V1:
        if slug not in existing:
            db.add(
                Interest(
                    name=name,
                    slug=slug,
                    display_order=display_order,
                    is_active=True,
                )
            )
            existing.add(slug)


def create_interest(
    db: Session,
    *,
    name: str,
    description: str | None = None,
    display_order: int = 0,
    is_active: bool = True,
) -> Interest:
    interest = Interest(
        name=name.strip(),
        slug=unique_slug(db, Interest, name, max_length=160),
        description=description,
        display_order=display_order,
        is_active=is_active,
    )
    db.add(interest)
    db.flush()
    return interest


def create_place(
    db: Session,
    *,
    district: District,
    name: str,
    destination: Destination | None = None,
    interests: list[Interest] | None = None,
    short_description: str | None = None,
    description: str | None = None,
    image_url: str | None = None,
    spiritual_tradition: SpiritualTradition | None = None,
    is_active: bool = True,
    is_featured: bool = False,
    display_order: int = 0,
) -> Place:
    if not name.strip():
        raise ValueError("Place name is required")
    if destination is not None and destination.district_id != district.id:
        raise ValueError("Place destination must belong to the selected district")
    unique_interests = list({item.id: item for item in interests or []}.values())
    place = Place(
        district_id=district.id,
        destination_id=destination.id if destination else None,
        name=name.strip(),
        slug=unique_slug(
            db,
            Place,
            name,
            scope=(Place.district_id == district.id,),
            max_length=180,
        ),
        short_description=short_description,
        description=description,
        image_url=image_url,
        spiritual_tradition=spiritual_tradition,
        is_active=is_active,
        is_featured=is_featured,
        display_order=display_order,
        interests=unique_interests,
        published_at=datetime.now(timezone.utc) if is_active else None,
    )
    db.add(place)
    db.flush()
    return place


def _interest(item: Interest) -> PublicInterestSummary:
    return PublicInterestSummary(
        name=item.name,
        slug=item.slug,
        description=item.description,
        display_order=item.display_order,
        path=f"/explore/{item.slug}",
    )


def _location(name: str, slug: str, path: str) -> PublicPlaceLocation:
    return PublicPlaceLocation(name=name, slug=slug, path=path)


def _summary(item: Place) -> PublicPlaceSummary:
    destination = item.destination
    return PublicPlaceSummary(
        name=item.name,
        slug=item.slug,
        short_description=item.short_description,
        image_url=item.image_url,
        image_alt=item.image_alt,
        image_status=item.media_asset.specificity if item.media_asset else None,
        is_featured=item.is_featured,
        district=_location(item.district.name, item.district.slug, f"/destinations/{item.district.slug}"),
        destination=(
            _location(
                destination.name,
                destination.slug,
                f"/destinations/{item.district.slug}/{destination.slug}",
            )
            if destination
            else None
        ),
        interests=[_interest(interest) for interest in sorted(item.interests, key=lambda value: (value.display_order, value.name)) if interest.is_active],
        path=f"/places/{item.district.slug}/{item.slug}",
    )


def _gallery(item: Place) -> list[PublicDiscoveryMedia]:
    return [
        PublicDiscoveryMedia(
            id=value.id, media_asset_id=value.asset.id, public_url=value.asset.public_url,
            alt_text=value.asset.alt_text, specificity=value.asset.specificity, role=value.role,
            display_order=value.display_order, attribution_text=value.asset.attribution_text,
            source_name=value.asset.source_name,
        )
        for value in item.media_items if value.role == "GALLERY" and value.asset.status == "ACTIVE"
    ]


def list_interests(db: Session) -> PublicInterestList:
    items = [_interest(item) for item in repository.list_interests(db)]
    return PublicInterestList(items=items, total=len(items))


def list_places(
    db: Session,
    *,
    query: str | None,
    district_slug: str | None,
    destination_slug: str | None,
    interest_slug: str | None,
    limit: int,
    offset: int,
) -> PublicPlaceList:
    items, total = repository.list_places(
        db,
        query=query,
        district_slug=district_slug,
        destination_slug=destination_slug,
        interest_slug=interest_slug,
        limit=limit,
        offset=offset,
    )
    return PublicPlaceList(
        items=[_summary(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_place(db: Session, district_slug: str, place_slug: str) -> PublicPlaceDetail:
    item = repository.get_place_by_slug(db, district_slug, place_slug)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return PublicPlaceDetail(
        **_summary(item).model_dump(),
        description=item.description,
        spiritual_tradition=item.spiritual_tradition,
        address=item.address,
        opening_hours=item.opening_hours,
        entry_fee_info=item.entry_fee_info,
        recommended_visit_duration=item.recommended_visit_duration,
        best_time_to_visit=item.best_time_to_visit,
        getting_there=item.getting_there,
        nearest_railway_station=item.nearest_railway_station,
        nearest_airport=item.nearest_airport,
        visitor_info_source=item.visitor_info_source,
        visitor_info_source_url=item.visitor_info_source_url,
        visitor_info_verified_at=item.visitor_info_verified_at,
        gallery=_gallery(item),
        faqs=[PublicFAQ(id=value.id, question=value.question, answer=value.answer, display_order=value.display_order) for value in item.faqs if value.is_active],
        related_places=[_summary(value) for value in repository.related_places(db, item)],
    )

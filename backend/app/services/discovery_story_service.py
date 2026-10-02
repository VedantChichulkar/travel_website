from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.discovery import DiscoveryStory
from app.repositories import discovery_story_repository as repository
from app.schemas.discovery_story import (
    PublicDiscoveryStoryDetail,
    PublicDiscoveryStoryList,
    PublicDiscoveryStorySummary,
    PublicStoryDestination,
    PublicStoryDistrict,
)
from app.schemas.place import PublicInterestSummary, PublicPlaceLocation, PublicPlaceSummary


def _interest(item) -> PublicInterestSummary:
    return PublicInterestSummary(
        name=item.name,
        slug=item.slug,
        description=item.description,
        display_order=item.display_order,
        path=f"/explore/{item.slug}",
    )


def _district(item) -> PublicStoryDistrict:
    return PublicStoryDistrict(name=item.name, slug=item.slug, path=f"/destinations/{item.slug}")


def _place_location(item) -> PublicPlaceLocation:
    return PublicPlaceLocation(name=item.name, slug=item.slug, path=f"/destinations/{item.slug}")


def _place(item) -> PublicPlaceSummary:
    district = _place_location(item.district)
    destination = None
    if item.destination:
        destination = PublicPlaceLocation(
            name=item.destination.name,
            slug=item.destination.slug,
            path=f"/destinations/{item.district.slug}/{item.destination.slug}",
        )
    return PublicPlaceSummary(
        name=item.name,
        slug=item.slug,
        short_description=item.short_description,
        image_url=item.image_url,
        image_alt=item.image_alt,
        image_status=item.media_asset.specificity if item.media_asset else None,
        is_featured=item.is_featured,
        district=district,
        destination=destination,
        interests=[_interest(interest) for interest in item.interests if interest.is_active],
        path=f"/places/{item.district.slug}/{item.slug}",
    )


def _summary(item: DiscoveryStory) -> PublicDiscoveryStorySummary:
    return PublicDiscoveryStorySummary(
        title=item.title,
        slug=item.slug,
        short_description=item.short_description,
        image_url=item.image_url,
        is_featured=item.is_featured,
        interests=[_interest(interest) for interest in item.interests if interest.is_active],
        districts=[_district(district) for district in item.districts if district.is_active],
        path=f"/discover/{item.slug}",
    )


def list_stories(
    db: Session,
    *,
    interest: str | None,
    district: str | None,
    query: str | None,
    limit: int,
) -> PublicDiscoveryStoryList:
    items = [
        _summary(item)
        for item in repository.list_stories(
            db,
            interest_slug=interest,
            district_slug=district,
            query=query,
            limit=limit,
        )
    ]
    return PublicDiscoveryStoryList(items=items, total=len(items))


def get_story(db: Session, slug: str) -> PublicDiscoveryStoryDetail:
    item = repository.get_story_by_slug(db, slug)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery story not found")
    summary = _summary(item)
    destinations = [
        PublicStoryDestination(
            name=destination.name,
            slug=destination.slug,
            district_name=destination.district.name,
            district_slug=destination.district.slug,
            path=f"/destinations/{destination.district.slug}/{destination.slug}",
        )
        for destination in item.destinations
        if destination.is_active and destination.district.is_active
    ]
    related_places = [
        _place(place)
        for place in item.related_places
        if place.is_active
        and place.district.is_active
        and (place.destination is None or place.destination.is_active)
    ]
    return PublicDiscoveryStoryDetail(
        **summary.model_dump(),
        body=item.body,
        destinations=destinations,
        related_places=related_places,
    )

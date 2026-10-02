"""Validation and idempotent upsert for operator-run DiscoveryStory data."""

from collections import Counter
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.slug import slugify
from app.data.discovery_stories.types import CuratedDiscoveryStory
from app.models.destination import Destination, District
from app.models.discovery import DiscoveryStory
from app.models.place import Interest, Place


class CuratedDiscoveryStoryValidationError(ValueError):
    """Raised before writes when reviewed editorial data cannot be resolved safely."""


@dataclass(frozen=True)
class DiscoveryStorySeedReport:
    created: int
    updated: int
    unchanged: int
    failed: int
    total_stories: int
    stories_by_interest: dict[str, int]
    statewide_stories: int

    def lines(self) -> list[str]:
        by_interest = ", ".join(f"{key}:{value}" for key, value in self.stories_by_interest.items()) or "none"
        return [
            f"created={self.created} updated={self.updated} unchanged={self.unchanged} failed={self.failed}",
            f"total_stories={self.total_stories}",
            f"stories_by_interest={by_interest}",
            f"statewide_stories={self.statewide_stories}",
        ]


@dataclass(frozen=True)
class _ResolvedStory:
    record: CuratedDiscoveryStory
    slug: str
    interests: tuple[Interest, ...]
    districts: tuple[District, ...]
    destinations: tuple[Destination, ...]
    related_places: tuple[Place, ...]


def _fail(index: int, record: CuratedDiscoveryStory, message: str) -> CuratedDiscoveryStoryValidationError:
    return CuratedDiscoveryStoryValidationError(f"{record.title.strip() or f'record #{index + 1}'}: {message}")


def _validate_sources(index: int, record: CuratedDiscoveryStory) -> None:
    if not record.sources:
        raise _fail(index, record, "at least one authoritative source is required")
    for source in record.sources:
        if not source.source_name.strip():
            raise _fail(index, record, "source_name cannot be empty")
        parsed = urlparse(source.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise _fail(index, record, f"malformed source URL: {source.source_url!r}")
        if not isinstance(source.source_last_verified_at, date):
            raise _fail(index, record, "source_last_verified_at must be a date")
        if source.source_last_verified_at > date.today():
            raise _fail(index, record, "source_last_verified_at cannot be in the future")


def validate_curated_discovery_stories(
    db: Session, records: tuple[CuratedDiscoveryStory, ...]
) -> tuple[_ResolvedStory, ...]:
    interests = {item.slug: item for item in db.scalars(select(Interest))}
    districts = {item.slug: item for item in db.scalars(select(District))}
    destinations = {(item.district.slug, item.slug): item for item in db.scalars(select(Destination).options(selectinload(Destination.district)))}
    places = {(item.district.slug, item.slug): item for item in db.scalars(select(Place).options(selectinload(Place.district)))}
    existing_titles = {item.title: item.slug for item in db.scalars(select(DiscoveryStory))}
    seen_slugs: set[str] = set()
    seen_titles: set[str] = set()
    resolved: list[_ResolvedStory] = []

    for index, record in enumerate(records):
        title = record.title.strip()
        if not title:
            raise _fail(index, record, "title is required")
        if len(title) > 180:
            raise _fail(index, record, "title exceeds 180 characters")
        if title in seen_titles:
            raise _fail(index, record, f"duplicate curated title {title!r}")
        seen_titles.add(title)
        if not record.short_description.strip() or not record.body.strip():
            raise _fail(index, record, "short_description and body are required")
        if len(record.short_description) > 500:
            raise _fail(index, record, "short_description exceeds 500 characters")
        if record.image_url is not None and len(record.image_url) > 2048:
            raise _fail(index, record, "image_url exceeds 2048 characters")
        if not isinstance(record.is_active, bool) or not isinstance(record.is_featured, bool):
            raise _fail(index, record, "visibility fields must be boolean")
        if isinstance(record.display_order, bool) or not isinstance(record.display_order, int) or record.display_order < 0:
            raise _fail(index, record, "display_order must be a non-negative integer")
        _validate_sources(index, record)

        canonical_slug = record.slug.strip().lower() if record.slug else slugify(title, max_length=200)
        if slugify(canonical_slug, max_length=200) != canonical_slug:
            raise _fail(index, record, f"invalid canonical slug {record.slug!r}")
        if canonical_slug in seen_slugs:
            raise _fail(index, record, f"duplicate curated slug {canonical_slug!r}")
        seen_slugs.add(canonical_slug)
        existing_slug = existing_titles.get(title)
        if existing_slug is not None and existing_slug != canonical_slug:
            raise _fail(index, record, f"title already belongs to story slug {existing_slug!r}")

        if not record.interest_slugs:
            raise _fail(index, record, "at least one Interest is required")
        if len(set(record.interest_slugs)) != len(record.interest_slugs):
            raise _fail(index, record, "duplicate Interest slugs are not allowed")
        resolved_interests = []
        for raw_slug in record.interest_slugs:
            interest = interests.get(raw_slug.strip().lower())
            if interest is None:
                raise _fail(index, record, f"unknown Interest slug {raw_slug!r}")
            resolved_interests.append(interest)

        if len(set(record.district_slugs)) != len(record.district_slugs):
            raise _fail(index, record, "duplicate district slugs are not allowed")
        resolved_districts = []
        for raw_slug in record.district_slugs:
            district = districts.get(raw_slug.strip().lower())
            if district is None:
                raise _fail(index, record, f"unknown district slug {raw_slug!r}")
            resolved_districts.append(district)

        resolved_destinations = []
        for reference in record.destination_references:
            destination = destinations.get((reference.district_slug.strip().lower(), reference.destination_slug.strip().lower()))
            if destination is None:
                raise _fail(index, record, f"unknown Destination {reference.district_slug}/{reference.destination_slug}")
            resolved_destinations.append(destination)
        if len({item.id for item in resolved_destinations}) != len(resolved_destinations):
            raise _fail(index, record, "duplicate Destination references are not allowed")

        resolved_places = []
        for reference in record.related_place_references:
            place = places.get((reference.district_slug.strip().lower(), reference.place_slug.strip().lower()))
            if place is None:
                raise _fail(index, record, f"unknown related Place {reference.district_slug}/{reference.place_slug}")
            resolved_places.append(place)
        if len({item.id for item in resolved_places}) != len(resolved_places):
            raise _fail(index, record, "duplicate related Place references are not allowed")

        resolved.append(
            _ResolvedStory(
                record=record,
                slug=canonical_slug,
                interests=tuple(resolved_interests),
                districts=tuple(resolved_districts),
                destinations=tuple(resolved_destinations),
                related_places=tuple(resolved_places),
            )
        )
    return tuple(resolved)


def seed_curated_discovery_stories(
    db: Session, records: tuple[CuratedDiscoveryStory, ...]
) -> DiscoveryStorySeedReport:
    resolved = validate_curated_discovery_stories(db, records)
    created = updated = unchanged = 0
    for item in resolved:
        story = db.scalar(
            select(DiscoveryStory)
            .where(DiscoveryStory.slug == item.slug)
            .options(
                selectinload(DiscoveryStory.interests),
                selectinload(DiscoveryStory.districts),
                selectinload(DiscoveryStory.destinations),
                selectinload(DiscoveryStory.related_places),
            )
        )
        if story is None:
            story = DiscoveryStory(slug=item.slug)
            db.add(story)
            created += 1
        changed = story.id is None
        managed_values = {
            "title": item.record.title,
            "short_description": item.record.short_description,
            "body": item.record.body,
            "image_url": item.record.image_url,
            "is_active": item.record.is_active,
            "is_featured": item.record.is_featured,
            "display_order": item.record.display_order,
        }
        for field, value in managed_values.items():
            if getattr(story, field, None) != value:
                setattr(story, field, value)
                changed = True
        for field, values in (
            ("interests", item.interests),
            ("districts", item.districts),
            ("destinations", item.destinations),
            ("related_places", item.related_places),
        ):
            current = getattr(story, field, [])
            if {value.id for value in current} != {value.id for value in values}:
                setattr(story, field, list(values))
                changed = True
        if story.id is not None:
            if changed:
                updated += 1
            else:
                unchanged += 1
    db.flush()
    return _report(db, created=created, updated=updated, unchanged=unchanged)


def _report(db: Session, *, created: int, updated: int, unchanged: int) -> DiscoveryStorySeedReport:
    stories = list(db.scalars(select(DiscoveryStory).options(selectinload(DiscoveryStory.interests), selectinload(DiscoveryStory.districts))).unique())
    by_interest: Counter[str] = Counter()
    for story in stories:
        for interest in story.interests:
            by_interest[interest.slug] += 1
    return DiscoveryStorySeedReport(
        created=created,
        updated=updated,
        unchanged=unchanged,
        failed=0,
        total_stories=len(stories),
        stories_by_interest=dict(sorted(by_interest.items())),
        statewide_stories=sum(not story.districts for story in stories),
    )

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.destination import Destination, District
from app.models.discovery import DiscoveryStory
from app.models.place import Interest, Place


LOAD_PUBLIC_RELATIONSHIPS = (
    selectinload(DiscoveryStory.interests),
    selectinload(DiscoveryStory.districts),
    selectinload(DiscoveryStory.destinations).selectinload(Destination.district),
    selectinload(DiscoveryStory.related_places).selectinload(Place.district),
    selectinload(DiscoveryStory.related_places).selectinload(Place.destination),
    selectinload(DiscoveryStory.related_places).selectinload(Place.interests),
)


def list_stories(
    db: Session,
    *,
    interest_slug: str | None = None,
    district_slug: str | None = None,
    query: str | None = None,
    limit: int = 100,
) -> list[DiscoveryStory]:
    statement = select(DiscoveryStory).where(DiscoveryStory.is_active.is_(True))
    if interest_slug:
        normalized = interest_slug.strip().lower()
        statement = statement.where(
            DiscoveryStory.interests.any(
                and_(Interest.slug == normalized, Interest.is_active.is_(True))
            )
        )
    if district_slug:
        normalized = district_slug.strip().lower()
        statement = statement.where(
            DiscoveryStory.districts.any(
                and_(District.slug == normalized, District.is_active.is_(True))
            )
        )
    if query:
        term = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                DiscoveryStory.title.ilike(term),
                DiscoveryStory.slug.ilike(term),
                DiscoveryStory.short_description.ilike(term),
            )
        )
    return list(
        db.scalars(
            statement.options(*LOAD_PUBLIC_RELATIONSHIPS)
            .order_by(
                DiscoveryStory.is_featured.desc(),
                DiscoveryStory.display_order,
                DiscoveryStory.title,
            )
            .limit(limit)
        ).unique()
    )


def get_story_by_slug(db: Session, slug: str, *, active_only: bool = True) -> DiscoveryStory | None:
    statement = select(DiscoveryStory).where(DiscoveryStory.slug == slug.strip().lower())
    if active_only:
        statement = statement.where(DiscoveryStory.is_active.is_(True))
    return db.scalar(statement.options(*LOAD_PUBLIC_RELATIONSHIPS))


def search_stories(db: Session, query: str, *, limit: int) -> list[DiscoveryStory]:
    if limit <= 0:
        return []
    term = f"%{query.strip()}%"
    return list(
        db.scalars(
            select(DiscoveryStory)
            .where(
                DiscoveryStory.is_active.is_(True),
                or_(DiscoveryStory.title.ilike(term), DiscoveryStory.slug.ilike(term)),
            )
            .order_by(DiscoveryStory.is_featured.desc(), DiscoveryStory.display_order, DiscoveryStory.title)
            .limit(limit)
        )
    )

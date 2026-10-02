from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.destination import Destination, District
from app.models.discovery_content import PlaceMedia
from app.models.place import Interest, Place


def list_interests(db: Session) -> list[Interest]:
    return list(
        db.scalars(
            select(Interest)
            .where(Interest.is_active.is_(True))
            .order_by(Interest.display_order, Interest.name)
        )
    )


def get_interest_by_slug(db: Session, slug: str, *, active_only: bool = True) -> Interest | None:
    statement = select(Interest).where(Interest.slug == slug.strip().lower())
    if active_only:
        statement = statement.where(Interest.is_active.is_(True))
    return db.scalar(statement)


def list_places(
    db: Session,
    *,
    query: str | None,
    district_slug: str | None,
    destination_slug: str | None,
    interest_slug: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Place], int]:
    statement = (
        select(Place)
        .join(Place.district)
        .where(Place.is_active.is_(True), District.is_active.is_(True))
    )
    if query:
        term = f"%{query.strip()}%"
        statement = statement.where(
            or_(
                Place.name.ilike(term),
                Place.slug.ilike(term),
                Place.short_description.ilike(term),
            )
        )
    if district_slug:
        statement = statement.where(District.slug == district_slug.strip().lower())
    if destination_slug:
        statement = statement.join(Place.destination).where(
            Destination.slug == destination_slug.strip().lower(),
            Destination.is_active.is_(True),
        )
    else:
        statement = statement.where(
            or_(Place.destination_id.is_(None), Place.destination.has(Destination.is_active.is_(True)))
        )
    if interest_slug:
        statement = statement.join(Place.interests).where(
            Interest.slug == interest_slug.strip().lower(),
            Interest.is_active.is_(True),
        )

    statement = statement.distinct()
    count_statement = select(func.count()).select_from(
        statement.with_only_columns(Place.id).order_by(None).subquery()
    )
    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(
            statement.options(
                selectinload(Place.district),
                selectinload(Place.destination),
                selectinload(Place.interests),
                selectinload(Place.media_asset),
                selectinload(Place.faqs),
                selectinload(Place.media_items).selectinload(PlaceMedia.asset),
            )
            .order_by(Place.is_featured.desc(), Place.display_order, Place.name)
            .offset(offset)
            .limit(limit)
        ).unique()
    )
    return items, total


def get_place_by_slug(
    db: Session, district_slug: str, place_slug: str, *, active_only: bool = True
) -> Place | None:
    statement = (
        select(Place)
        .join(Place.district)
        .where(
            District.slug == district_slug.strip().lower(),
            Place.slug == place_slug.strip().lower(),
        )
        .options(
            selectinload(Place.district),
            selectinload(Place.destination),
            selectinload(Place.interests),
            selectinload(Place.media_asset),
            selectinload(Place.faqs),
            selectinload(Place.media_items).selectinload(PlaceMedia.asset),
        )
    )
    if active_only:
        statement = statement.where(
            Place.is_active.is_(True),
            District.is_active.is_(True),
            or_(Place.destination_id.is_(None), Place.destination.has(Destination.is_active.is_(True))),
        )
    return db.scalar(statement)


def related_places(db: Session, item: Place, *, limit: int = 6) -> list[Place]:
    statement = (
        select(Place)
        .join(Place.district)
        .where(
            Place.id != item.id, Place.is_active.is_(True), District.is_active.is_(True),
            or_(Place.destination_id.is_(None), Place.destination.has(Destination.is_active.is_(True))),
        )
    )
    if item.destination_id is not None:
        statement = statement.where(Place.destination_id == item.destination_id)
    else:
        statement = statement.where(Place.district_id == item.district_id)
    return list(db.scalars(statement.options(
        selectinload(Place.district), selectinload(Place.destination), selectinload(Place.interests),
        selectinload(Place.media_asset),
    ).order_by(Place.is_featured.desc(), Place.display_order, Place.name).limit(limit)).unique())

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.place import PublicInterestList, PublicPlaceDetail, PublicPlaceList
from app.services import place_service


places_router = APIRouter()
interests_router = APIRouter()


@places_router.get("", response_model=PublicPlaceList)
def list_places(
    q: str | None = Query(default=None, min_length=2, max_length=100),
    district: str | None = Query(default=None, min_length=1, max_length=140),
    destination: str | None = Query(default=None, min_length=1, max_length=160),
    interest: str | None = Query(default=None, min_length=1, max_length=160),
    limit: int = Query(default=24, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return place_service.list_places(
        db,
        query=q,
        district_slug=district,
        destination_slug=destination,
        interest_slug=interest,
        limit=limit,
        offset=offset,
    )


@places_router.get("/{district_slug}/{place_slug}", response_model=PublicPlaceDetail)
def get_place(district_slug: str, place_slug: str, db: Session = Depends(get_db)):
    return place_service.get_place(db, district_slug, place_slug)


@interests_router.get("", response_model=PublicInterestList)
def list_interests(db: Session = Depends(get_db)):
    return place_service.list_interests(db)


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.destination import (
    DestinationSearchResponse,
    PublicDestinationList,
    PublicDestinationDetail,
    PublicDestinationSummary,
    PublicDistrictDetail,
    PublicDistrictList,
)
from app.services import destination_service


router = APIRouter()


@router.get("", response_model=PublicDistrictList)
def list_districts(
    q: str | None = Query(default=None, min_length=2, max_length=100),
    db: Session = Depends(get_db),
):
    return destination_service.list_districts(db, q)


@router.get("/search", response_model=DestinationSearchResponse)
def search_destinations(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=10, ge=1, le=25),
    include_places: bool = Query(default=False),
    include_stories: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return destination_service.search(
        db, q, limit, include_places=include_places, include_stories=include_stories
    )


@router.get("/{district_slug}/places", response_model=PublicDestinationList)
def list_destinations(district_slug: str, db: Session = Depends(get_db)):
    return destination_service.list_destinations(db, district_slug)


@router.get("/{district_slug}/{destination_slug}", response_model=PublicDestinationDetail)
def get_destination(district_slug: str, destination_slug: str, db: Session = Depends(get_db)):
    return destination_service.get_destination(db, district_slug, destination_slug)


@router.get("/{district_slug}", response_model=PublicDistrictDetail)
def get_district(district_slug: str, db: Session = Depends(get_db)):
    return destination_service.get_district(db, district_slug)

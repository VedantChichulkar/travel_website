from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.hotel import PropertyType
from app.schemas.public_hotel import (
    PublicHotelDetail,
    PublicHotelSearchResponse,
    PublicHotelSort,
    PublicRoomAvailabilityResponse,
)
from app.services import public_hotel_service
from app.schemas.review import PublicReview, PublicReviewList
from app.services import review_service


router = APIRouter()


@router.get("/{hotel_ref}/reviews", response_model=PublicReviewList)
def get_reviews(hotel_ref: str, db: Session = Depends(get_db)):
    hotel = public_hotel_service.resolve_hotel(db, hotel_ref)
    items = review_service.list_public(db, hotel.id)
    average = round(sum(item.overall_rating for item in items) / len(items), 2) if items else None
    return PublicReviewList(items=[PublicReview.model_validate(item) for item in items], total=len(items), average_overall_rating=average)


@router.get("", response_model=PublicHotelSearchResponse)
def search_hotels(
    city: str | None = Query(default=None, min_length=2, max_length=100),
    district: str | None = Query(default=None, min_length=2, max_length=100),
    destination: str | None = Query(default=None, min_length=2, max_length=300),
    check_in: date | None = None,
    check_out: date | None = None,
    adults: int = Query(default=1, ge=1, le=20),
    children: int = Query(default=0, ge=0, le=20),
    rooms: int = Query(default=1, ge=1, le=10),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    star_rating: int | None = Query(default=None, ge=0, le=5),
    property_type: PropertyType | None = None,
    amenities: list[str] = Query(default_factory=list),
    sort: PublicHotelSort = PublicHotelSort.RECOMMENDED,
    db: Session = Depends(get_db),
):
    return public_hotel_service.search_hotels(
        db,
        city=city,
        district=district,
        destination=destination,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        rooms=rooms,
        min_price=min_price,
        max_price=max_price,
        star_rating=star_rating,
        property_type=property_type,
        amenities=amenities,
        sort=sort,
    )


@router.get("/{hotel_ref}", response_model=PublicHotelDetail)
def get_hotel(hotel_ref: str, db: Session = Depends(get_db)):
    return public_hotel_service.get_hotel(db, hotel_ref)


@router.get("/{hotel_ref}/rooms", response_model=PublicRoomAvailabilityResponse)
def get_rooms(
    hotel_ref: str,
    check_in: date,
    check_out: date,
    adults: int = Query(default=1, ge=1, le=20),
    children: int = Query(default=0, ge=0, le=20),
    rooms: int = Query(default=1, ge=1, le=10),
    db: Session = Depends(get_db),
):
    return public_hotel_service.get_rooms(
        db,
        hotel_ref,
        check_in=check_in,
        check_out=check_out,
        adults=adults,
        children=children,
        rooms=rooms,
    )

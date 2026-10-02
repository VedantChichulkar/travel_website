from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.permission import require_admin
from app.dependencies import get_db
from app.schemas.hotel import (
    AmenityAssignment,
    AmenityCreate,
    AmenityResponse,
    BookingGatewayOverrideUpdate,
    BookingGatewayStateResponse,
    HotelCreate,
    HotelDetailResponse,
    HotelImageCreate,
    HotelImageResponse,
    HotelPolicyCreate,
    HotelPolicyResponse,
    HotelPolicyUpdate,
    HotelResponse,
    HotelStatusUpdate,
    HotelUpdate,
    RoomImageCreate,
    RoomImageResponse,
    RoomInventoryCreate,
    RoomInventoryResponse,
    RoomInventoryUpdate,
    RoomStatusUpdate,
    RoomTypeCreate,
    RoomTypeResponse,
    RoomTypeUpdate,
    PartnerRoomTypeResponse,
    RoomTypeReviewRequest,
)
from app.models.hotel import HotelStatus, RoomTypeStatus
from app.models.user import User
from app.services import admin_control_service, booking_gateway_service, hotel_service, inventory_service
from app.services import partner_room_service


router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/hotels", response_model=HotelResponse, status_code=status.HTTP_201_CREATED)
def create_hotel(data: HotelCreate, db: Session = Depends(get_db)):
    return hotel_service.create_hotel(db, data)


@router.get("/hotels", response_model=list[HotelResponse])
def list_hotels(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None, min_length=1, max_length=160),
    hotel_status: HotelStatus | None = None,
    db: Session = Depends(get_db),
):
    return hotel_service.list_hotels(db, offset=offset, limit=limit, search=search, hotel_status=hotel_status)


@router.get("/hotels/{hotel_id}", response_model=HotelDetailResponse)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):
    return hotel_service.get_hotel(db, hotel_id)


@router.patch("/hotels/{hotel_id}", response_model=HotelResponse)
def update_hotel(hotel_id: int, data: HotelUpdate, db: Session = Depends(get_db)):
    return hotel_service.update_hotel(db, hotel_id, data)


@router.patch("/hotels/{hotel_id}/status", response_model=HotelResponse, deprecated=True)
def update_hotel_status(hotel_id: int, data: HotelStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Legacy compatibility route backed by the audited governance service."""
    return admin_control_service.update_hotel_status(db, current_user, hotel_id, data.status, data.reason)


@router.get("/hotels/{hotel_id}/booking-gateway", response_model=BookingGatewayStateResponse)
def get_hotel_booking_gateway(hotel_id: int, db: Session = Depends(get_db)):
    hotel = hotel_service.get_hotel(db, hotel_id, detailed=False)
    return booking_gateway_service.state(db, hotel)


@router.put("/hotels/{hotel_id}/booking-gateway/override", response_model=BookingGatewayStateResponse)
def override_hotel_booking_gateway(hotel_id: int, data: BookingGatewayOverrideUpdate, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    hotel = hotel_service.get_hotel(db, hotel_id, detailed=False)
    return booking_gateway_service.set_override(db, hotel, current_user, data.booking_gateway_status, data.reason)


@router.delete("/hotels/{hotel_id}/booking-gateway/override", response_model=BookingGatewayStateResponse)
def clear_hotel_booking_gateway_override(hotel_id: int, reason: str = Query(..., min_length=5, max_length=1000), db: Session = Depends(get_db), current_user=Depends(require_admin)):
    hotel = hotel_service.get_hotel(db, hotel_id, detailed=False)
    return booking_gateway_service.clear_override(db, hotel, current_user, reason)


@router.post(
    "/hotels/{hotel_id}/images",
    response_model=HotelImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_hotel_image(hotel_id: int, data: HotelImageCreate, db: Session = Depends(get_db)):
    return hotel_service.add_hotel_image(db, hotel_id, data)


@router.delete("/hotels/{hotel_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hotel_image(hotel_id: int, image_id: int, db: Session = Depends(get_db)) -> Response:
    hotel_service.delete_hotel_image(db, hotel_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/amenities", response_model=AmenityResponse, status_code=status.HTTP_201_CREATED)
def create_amenity(data: AmenityCreate, db: Session = Depends(get_db)):
    return hotel_service.create_amenity(db, data)


@router.get("/amenities", response_model=list[AmenityResponse])
def list_amenities(
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    return hotel_service.list_amenities(db, active_only=active_only)


@router.put("/hotels/{hotel_id}/amenities", response_model=list[AmenityResponse])
def assign_amenities(hotel_id: int, data: AmenityAssignment, db: Session = Depends(get_db)):
    return hotel_service.assign_amenities(db, hotel_id, data)


@router.post(
    "/hotels/{hotel_id}/policy",
    response_model=HotelPolicyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_policy(hotel_id: int, data: HotelPolicyCreate, db: Session = Depends(get_db)):
    return hotel_service.create_policy(db, hotel_id, data)


@router.get("/hotels/{hotel_id}/policy", response_model=HotelPolicyResponse)
def get_policy(hotel_id: int, db: Session = Depends(get_db)):
    return hotel_service.get_policy(db, hotel_id)


@router.patch("/hotels/{hotel_id}/policy", response_model=HotelPolicyResponse)
def update_policy(hotel_id: int, data: HotelPolicyUpdate, db: Session = Depends(get_db)):
    return hotel_service.update_policy(db, hotel_id, data)


@router.post(
    "/hotels/{hotel_id}/rooms",
    response_model=RoomTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_room_type(hotel_id: int, data: RoomTypeCreate, db: Session = Depends(get_db)):
    return hotel_service.create_room_type(db, hotel_id, data)


@router.get("/hotels/{hotel_id}/rooms", response_model=list[RoomTypeResponse])
def list_room_types(hotel_id: int, db: Session = Depends(get_db)):
    return hotel_service.list_room_types(db, hotel_id)


@router.get("/rooms/review-queue", response_model=list[PartnerRoomTypeResponse])
def room_review_queue(room_status: RoomTypeStatus | None = None, db: Session = Depends(get_db)):
    return partner_room_service.list_admin_review_queue(db, room_status)


@router.get("/rooms/{room_type_id}", response_model=RoomTypeResponse)
def get_room_type(room_type_id: int, db: Session = Depends(get_db)):
    return hotel_service.get_room_type(db, room_type_id)


@router.patch("/rooms/{room_type_id}", response_model=RoomTypeResponse)
def update_room_type(room_type_id: int, data: RoomTypeUpdate, db: Session = Depends(get_db)):
    return hotel_service.update_room_type(db, room_type_id, data)


@router.patch("/rooms/{room_type_id}/status", response_model=RoomTypeResponse)
def update_room_status(room_type_id: int, data: RoomStatusUpdate, db: Session = Depends(get_db)):
    return hotel_service.update_room_status(db, room_type_id, data.is_active)


@router.post("/rooms/{room_type_id}/review", response_model=PartnerRoomTypeResponse)
def review_room_type(room_type_id: int, data: RoomTypeReviewRequest, db: Session = Depends(get_db), current_user=Depends(require_admin)):
    return partner_room_service.review_room(db, current_user, room_type_id, data)


@router.post(
    "/rooms/{room_type_id}/images",
    response_model=RoomImageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_room_image(room_type_id: int, data: RoomImageCreate, db: Session = Depends(get_db)):
    return hotel_service.add_room_image(db, room_type_id, data)


@router.delete("/rooms/{room_type_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room_image(room_type_id: int, image_id: int, db: Session = Depends(get_db)) -> Response:
    hotel_service.delete_room_image(db, room_type_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/rooms/{room_type_id}/inventory",
    response_model=RoomInventoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory(room_type_id: int, data: RoomInventoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    room = hotel_service.get_room_type(db, room_type_id)
    return inventory_service.create_admin_inventory(db, room, data, current_user)


@router.get("/rooms/{room_type_id}/inventory", response_model=list[RoomInventoryResponse])
def list_inventory(
    room_type_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    room = hotel_service.get_room_type(db, room_type_id)
    return inventory_service.list_inventory(db, room, start_date=start_date, end_date=end_date)


@router.patch("/inventory/{inventory_id}", response_model=RoomInventoryResponse)
def update_inventory(
    inventory_id: int,
    data: RoomInventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return inventory_service.update_admin_inventory(db, inventory_id, data, current_user)

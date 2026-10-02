from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.permission import require_hotel_partner, require_hotel_partner_only
from app.dependencies import get_db
from app.models.user import User
from app.schemas.hotel import (
    AmenityAssignment,
    AmenityResponse,
    HotelCreate,
    HotelImageCreate,
    HotelImageResponse,
    HotelImageOrderUpdate,
    HotelResponse,
    HotelUpdate,
    PartnerHotelProfileResponse,
    PartnerHotelProfileUpdate,
    PartnerRoomTypeCreate,
    PartnerRoomTypeResponse,
    PartnerRoomTypeUpdate,
    RoomImageCreate,
    RoomImageResponse,
    PartnerInventoryRangeResponse,
    PartnerInventoryRangeUpdate,
    BookingGatewayStateResponse,
    HotelBookingGatewayUpdate,
)
from app.repositories import hotel_repository
from app.schemas.hotel_verification import (
    HotelVerificationResponse,
    PartnerHotelOverviewResponse,
    VerificationSubmitRequest,
    PrivateDocumentUploadResponse,
    VerificationFeeStatusResponse,
)
from app.schemas.booking import BookingListResponse, BookingRequestDecision, BookingResponse, CheckInIssueRequest, CheckInRequest, OperationBoardResponse, OperationBookingResponse, OperationLookupRequest, PaymentOrderResponse
from app.services import booking_service, partner_hotel_service, payment_service, private_document_storage
from app.services import booking_gateway_service, hotel_operations_service, hotel_service, inventory_service, partner_room_service
from app.schemas.settlement import PartnerSettlementResponse
from app.services import settlement_service
from app.schemas.review import HotelReviewResponseCreate, ReviewChallengeCreate, ReviewRead
from app.services import review_service


router = APIRouter(dependencies=[Depends(require_hotel_partner_only)])


@router.get("/booking-requests", response_model=BookingListResponse)
def list_booking_requests(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    """Return only request-mode bookings belonging to the authenticated partner's hotel."""
    return booking_service.list_partner_requests(db, current_user)


@router.get("/bookings", response_model=BookingListResponse)
def list_partner_bookings(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return booking_service.list_partner_bookings(db, current_user)


@router.post("/booking-requests/{booking_id}/accept", response_model=BookingResponse)
def accept_booking_request(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return booking_service.accept_request(db, current_user, booking_id)


@router.post("/booking-requests/{booking_id}/reject", response_model=BookingResponse)
def reject_booking_request(booking_id: int, data: BookingRequestDecision, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return booking_service.reject_request(db, current_user, booking_id, data.reason)


@router.get("/reviews", response_model=list[ReviewRead])
def list_reviews(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return review_service.list_partner(db, current_user)


@router.post("/reviews/{review_id}/response", response_model=ReviewRead)
def respond_to_review(review_id: int, data: HotelReviewResponseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return review_service.respond(db, current_user, review_id, data.response_text)


@router.post("/reviews/{review_id}/challenge", response_model=ReviewRead)
def challenge_review(review_id: int, data: ReviewChallengeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return review_service.challenge(db, current_user, review_id, data)


@router.get("/settlements", response_model=list[PartnerSettlementResponse])
def list_settlements(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return settlement_service.list_partner(db, current_user)


@router.get("/settlements/{settlement_id}", response_model=PartnerSettlementResponse)
def get_settlement(settlement_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return settlement_service.get_partner(db, current_user, settlement_id)


@router.get("/operations", response_model=OperationBoardResponse)
def list_operation_board(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> OperationBoardResponse:
    groups = hotel_operations_service.list_board(db, current_user)
    return OperationBoardResponse(
        generated_at=datetime.now(timezone.utc),
        **{name: [OperationBookingResponse.from_booking(booking) for booking in bookings] for name, bookings in groups.items()},
    )


@router.post("/operations/lookup", response_model=OperationBookingResponse)
def lookup_operation_booking(data: OperationLookupRequest, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return OperationBookingResponse.from_booking(hotel_operations_service.lookup(db, current_user, booking_id=data.booking_id, booking_reference=data.booking_reference, qr_token=data.qr_token))


@router.post("/operations/bookings/{booking_id}/check-in", response_model=OperationBookingResponse)
def check_in_booking(booking_id: int, data: CheckInRequest, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return OperationBookingResponse.from_booking(hotel_operations_service.check_in(db, current_user, booking_id, data.assigned_room))


@router.post("/operations/bookings/{booking_id}/check-out", response_model=OperationBookingResponse)
def check_out_booking(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return OperationBookingResponse.from_booking(hotel_operations_service.check_out(db, current_user, booking_id))


@router.post("/operations/bookings/{booking_id}/check-in-issue", response_model=OperationBookingResponse)
def report_check_in_issue(booking_id: int, data: CheckInIssueRequest, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return OperationBookingResponse.from_booking(hotel_operations_service.report_issue(db, current_user, booking_id, data.issue_type.value, data.reason))


@router.post("/operations/bookings/{booking_id}/no-show", response_model=OperationBookingResponse)
def report_no_show(booking_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return OperationBookingResponse.from_booking(hotel_operations_service.report_no_show(db, current_user, booking_id))


@router.post("/operations/run-fallbacks", response_model=list[OperationBookingResponse])
def run_operation_fallbacks(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)):
    return [OperationBookingResponse.from_booking(item) for item in hotel_operations_service.run_fallbacks(db, current_user)]


@router.get("/booking-gateway", response_model=BookingGatewayStateResponse)
def get_booking_gateway(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> BookingGatewayStateResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, current_user.id)
    if hotel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return booking_gateway_service.state(db, hotel)


@router.patch("/booking-gateway", response_model=BookingGatewayStateResponse)
def update_booking_gateway(data: HotelBookingGatewayUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> BookingGatewayStateResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, current_user.id)
    if hotel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return booking_gateway_service.update_partner(db, hotel, data.booking_gateway_status)


@router.get("/room-types", response_model=list[PartnerRoomTypeResponse])
def list_room_types(db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> list[PartnerRoomTypeResponse]:
    return partner_room_service.list_partner_rooms(db, current_user)


@router.post("/room-types", response_model=PartnerRoomTypeResponse, status_code=status.HTTP_201_CREATED)
def create_room_type(data: PartnerRoomTypeCreate, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> PartnerRoomTypeResponse:
    return partner_room_service.create_partner_room(db, current_user, data)


@router.get("/room-types/{room_id}", response_model=PartnerRoomTypeResponse)
def get_room_type(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> PartnerRoomTypeResponse:
    return partner_room_service.get_partner_room(db, current_user, room_id)


@router.put("/room-types/{room_id}", response_model=PartnerRoomTypeResponse)
def update_room_type(room_id: int, data: PartnerRoomTypeUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> PartnerRoomTypeResponse:
    return partner_room_service.update_partner_room(db, current_user, room_id, data)


@router.delete("/room-types/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room_type(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> Response:
    partner_room_service.delete_partner_room(db, current_user, room_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/room-types/{room_id}/inventory", response_model=PartnerInventoryRangeResponse)
def list_room_inventory(
    room_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> PartnerInventoryRangeResponse:
    room = partner_room_service.get_owned_room(db, current_user, room_id)
    items = inventory_service.list_partner_inventory(db, room, start_date, end_date)
    return PartnerInventoryRangeResponse(items=items, last_inventory_update=max((item.updated_at for item in items), default=None))


@router.put("/room-types/{room_id}/inventory", response_model=PartnerInventoryRangeResponse)
def update_room_inventory(
    room_id: int,
    data: PartnerInventoryRangeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> PartnerInventoryRangeResponse:
    room = partner_room_service.get_owned_room(db, current_user, room_id)
    items = inventory_service.update_partner_range(db, room, data)
    return PartnerInventoryRangeResponse(items=items, last_inventory_update=max((item.updated_at for item in items), default=None))


@router.post("/room-types/{room_id}/submit", response_model=PartnerRoomTypeResponse)
def submit_room_type(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> PartnerRoomTypeResponse:
    return partner_room_service.submit_partner_room(db, current_user, room_id)


@router.post("/room-types/{room_id}/images", response_model=RoomImageResponse, status_code=status.HTTP_201_CREATED)
def add_room_type_image(room_id: int, data: RoomImageCreate, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> RoomImageResponse:
    return partner_room_service.add_partner_room_image(db, current_user, room_id, data)


@router.post("/room-types/{room_id}/images/upload", response_model=RoomImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_room_type_image(
    room_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None, max_length=255),
    is_cover: bool = Form(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> RoomImageResponse:
    return await partner_room_service.upload_partner_room_image(
        db, current_user, room_id, file, alt_text=alt_text, is_cover=is_cover
    )


@router.patch("/room-types/{room_id}/images/{image_id}/cover", response_model=RoomImageResponse)
def set_room_type_cover_image(
    room_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> RoomImageResponse:
    return partner_room_service.set_partner_room_cover_image(db, current_user, room_id, image_id)


@router.delete("/room-types/{room_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room_type_image(room_id: int, image_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)) -> Response:
    partner_room_service.delete_partner_room_image(db, current_user, room_id, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/profile", response_model=PartnerHotelProfileResponse)
def get_profile(
    db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)
) -> PartnerHotelProfileResponse:
    return partner_hotel_service.get_partner_profile(db, current_user)


@router.patch("/profile", response_model=PartnerHotelProfileResponse)
def update_profile(
    data: PartnerHotelProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> PartnerHotelProfileResponse:
    return partner_hotel_service.update_partner_profile(db, current_user, data)


@router.get("/profile/facilities", response_model=list[AmenityResponse])
def list_profile_facilities(
    db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner_only)
) -> list[AmenityResponse]:
    return [AmenityResponse.model_validate(item) for item in hotel_repository.list_amenities(db, active_only=True)]


@router.put("/profile/facilities", response_model=PartnerHotelProfileResponse)
def replace_profile_facilities(
    data: AmenityAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> PartnerHotelProfileResponse:
    return partner_hotel_service.replace_partner_amenities(db, current_user, data)


@router.post("/profile/images", response_model=HotelImageResponse, status_code=status.HTTP_201_CREATED)
def add_profile_image(
    data: HotelImageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> HotelImageResponse:
    return partner_hotel_service.add_partner_image(db, current_user, data)


@router.post("/profile/images/upload", response_model=HotelImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_profile_image(
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None, max_length=255),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> HotelImageResponse:
    return await partner_hotel_service.upload_partner_image(db, current_user, file, alt_text=alt_text)


@router.patch("/profile/images/{image_id}/primary", response_model=HotelImageResponse)
def set_profile_primary_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> HotelImageResponse:
    return partner_hotel_service.set_partner_primary_image(db, current_user, image_id)


@router.put("/profile/images/order", response_model=list[HotelImageResponse])
def reorder_profile_images(
    data: HotelImageOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> list[HotelImageResponse]:
    return partner_hotel_service.reorder_partner_images(db, current_user, data)


@router.delete("/profile/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner_only),
) -> Response:
    partner_hotel_service.delete_partner_image(db, current_user, image_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/hotel",
    response_model=HotelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create hotel profile for authenticated partner",
)
def create_hotel(
    data: HotelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner),
) -> HotelResponse:
    return partner_hotel_service.create_partner_hotel(db, current_user, data)


@router.get(
    "/hotel",
    response_model=PartnerHotelOverviewResponse,
    summary="Get authenticated partner's hotel and onboarding status",
)
def get_hotel_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner),
) -> PartnerHotelOverviewResponse:
    return partner_hotel_service.get_partner_overview(db, current_user)


@router.get("/verification/fee", response_model=VerificationFeeStatusResponse)
def get_verification_fee(
    db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner)
) -> VerificationFeeStatusResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, current_user.id)
    if hotel is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return payment_service.verification_fee_status(db, hotel.id)


@router.post(
    "/verification/fee/payment-order",
    response_model=PaymentOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_verification_fee_payment_order(
    db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner)
) -> PaymentOrderResponse:
    return payment_service.create_verification_fee_order(db, current_user)


@router.patch(
    "/hotel",
    response_model=HotelResponse,
    summary="Update authenticated partner's hotel profile",
)
def update_hotel(
    data: HotelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner),
) -> HotelResponse:
    return partner_hotel_service.update_partner_hotel(db, current_user, data)


@router.post(
    "/verification",
    response_model=HotelVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit or update hotel verification information",
)
def submit_verification(
    data: VerificationSubmitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner),
) -> HotelVerificationResponse:
    return partner_hotel_service.submit_partner_verification(db, current_user, data)


@router.get(
    "/verification",
    response_model=HotelVerificationResponse,
    summary="Get verification status and review feedback",
)
def get_verification(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hotel_partner),
) -> HotelVerificationResponse:
    return partner_hotel_service.get_partner_verification(db, current_user)


@router.post("/verification/document", response_model=PrivateDocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_verification_document(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner)) -> PrivateDocumentUploadResponse:
    return await partner_hotel_service.upload_partner_verification_document(db, current_user, file)


@router.get("/verification/{verification_id}/document", response_class=StreamingResponse)
def download_verification_document(verification_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_hotel_partner)) -> StreamingResponse:
    verification = partner_hotel_service.get_partner_verification_document(db, current_user, verification_id)
    return private_document_storage.download_response(verification.document_storage_key, filename=verification.document_original_name or "verification-document", content_type=verification.document_content_type or "application/octet-stream")

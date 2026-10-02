from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hotel import BookingGatewayStatus, Hotel, HotelImage, HotelStatus
from app.models.hotel_verification import HotelVerification, VerificationStatus
from app.models.booking import PaymentStatus
from app.models.user import User
from app.repositories import hotel_repository, hotel_verification_repository
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
)
from app.services import audit_service, media_storage, payment_service, private_document_lifecycle_service, private_document_storage
from app.schemas.hotel_verification import (
    HotelVerificationResponse,
    PartnerHotelOverviewResponse,
    VerificationSubmitRequest,
    PrivateDocumentUploadResponse,
)


def create_partner_hotel(db: Session, user: User, data: HotelCreate) -> HotelResponse:
    existing_hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if existing_hotel is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hotel partner already has a registered hotel property",
        )

    if hotel_repository.get_hotel_by_slug(db, data.slug) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A hotel with this slug already exists",
        )

    hotel = Hotel(
        name=data.name,
        slug=data.slug,
        description=data.description,
        property_type=data.property_type,
        star_rating=data.star_rating,
        status=HotelStatus.DRAFT,
        booking_gateway_status=BookingGatewayStatus.PAUSED,
        partner_booking_gateway_status=BookingGatewayStatus.PAUSED,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        city=data.city,
        district=data.district,
        state=data.state,
        country=data.country,
        postal_code=data.postal_code,
        latitude=data.latitude,
        longitude=data.longitude,
        contact_email=data.contact_email or user.email,
        contact_phone=data.contact_phone or user.phone,
        partner_id=user.id,
        check_in_time=data.check_in_time,
        check_out_time=data.check_out_time,
        is_featured=data.is_featured,
    )
    db.add(hotel)
    db.commit()
    db.refresh(hotel)
    return HotelResponse.model_validate(hotel)


def get_partner_overview(db: Session, user: User) -> PartnerHotelOverviewResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        return PartnerHotelOverviewResponse(
            hotel=None,
            verification=None,
            has_hotel=False,
            is_onboarding_complete=False,
            can_access_portal=False,
            verification_fee=None,
        )

    verification = hotel_verification_repository.get_verification_by_hotel_id(db, hotel.id)

    can_access = (
        hotel.status == HotelStatus.ACTIVE
        and verification is not None
        and verification.verification_status == VerificationStatus.APPROVED
    )
    is_onboarding_complete = verification is not None and verification.submitted_at is not None

    fee = payment_service.verification_fee_status(db, hotel.id)
    verification_response = HotelVerificationResponse.model_validate(verification) if verification else None
    if verification_response:
        verification_response.fee = fee
    return PartnerHotelOverviewResponse(
        hotel=HotelResponse.model_validate(hotel),
        verification=verification_response,
        has_hotel=True,
        is_onboarding_complete=is_onboarding_complete,
        can_access_portal=can_access,
        verification_fee=fee,
    )


def update_partner_hotel(db: Session, user: User, data: HotelUpdate) -> HotelResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hotel found for this partner account",
        )

    if data.slug is not None and data.slug != hotel.slug:
        existing_slug = hotel_repository.get_hotel_by_slug(db, data.slug)
        if existing_slug is not None and existing_slug.id != hotel.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A hotel with this slug already exists",
            )

    update_dict = data.model_dump(exclude_unset=True)
    # Legacy onboarding update: operational and admin-controlled fields stay protected.
    for field, value in update_dict.items():
        if field in {"booking_gateway_status", "is_featured", "partner_id"}:
            continue
        setattr(hotel, field, value)

    _refresh_profile_completion(hotel)
    db.commit()
    db.refresh(hotel)
    return HotelResponse.model_validate(hotel)


def _refresh_profile_completion(hotel: Hotel) -> None:
    required = [
        hotel.name, hotel.description, hotel.property_type, hotel.address_line1, hotel.city,
        hotel.district, hotel.state == "Maharashtra", hotel.postal_code, hotel.contact_email,
        hotel.contact_phone, hotel.check_in_time, hotel.check_out_time,
    ]
    completed = sum(bool(item) for item in required) + bool(hotel.amenities) + bool(hotel.images)
    total = len(required) + 2
    hotel.profile_completion_percent = round(completed * 100 / total)
    hotel.is_profile_complete = completed == total


def _partner_hotel_or_404(db: Session, user: User) -> Hotel:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    return hotel


def get_partner_profile(db: Session, user: User) -> PartnerHotelProfileResponse:
    hotel = _partner_hotel_or_404(db, user)
    _refresh_profile_completion(hotel)
    db.commit()
    verification = hotel_verification_repository.get_verification_by_hotel_id(db, hotel.id)
    return PartnerHotelProfileResponse(
        **HotelResponse.model_validate(hotel).model_dump(),
        images=[HotelImageResponse.model_validate(image) for image in hotel.images],
        amenities=[AmenityResponse.model_validate(amenity) for amenity in hotel.amenities if amenity.is_active],
        verification_status=verification.verification_status.value if verification else None,
    )


def update_partner_profile(db: Session, user: User, data: PartnerHotelProfileUpdate) -> PartnerHotelProfileResponse:
    hotel = _partner_hotel_or_404(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hotel, field, value)
    _refresh_profile_completion(hotel)
    db.commit()
    return get_partner_profile(db, user)


def replace_partner_amenities(db: Session, user: User, data: AmenityAssignment) -> PartnerHotelProfileResponse:
    hotel = _partner_hotel_or_404(db, user)
    amenities = [hotel_repository.get_amenity_by_id(db, amenity_id) for amenity_id in data.amenity_ids]
    if any(amenity is None or not amenity.is_active for amenity in amenities):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="One or more facilities are unavailable")
    hotel.amenities = amenities
    _refresh_profile_completion(hotel)
    db.commit()
    return get_partner_profile(db, user)


def add_partner_image(db: Session, user: User, data: HotelImageCreate) -> HotelImageResponse:
    hotel = _partner_hotel_or_404(db, user)
    if data.is_cover:
        for image in hotel.images:
            image.is_cover = False
    image = HotelImage(hotel_id=hotel.id, **data.model_dump())
    db.add(image)
    hotel.images.append(image)
    _refresh_profile_completion(hotel)
    db.commit()
    db.refresh(image)
    return HotelImageResponse.model_validate(image)


async def upload_partner_image(
    db: Session,
    user: User,
    file: UploadFile,
    *,
    alt_text: str | None,
) -> HotelImageResponse:
    hotel = _partner_hotel_or_404(db, user)
    image_url, storage_key, content_type, file_size = await media_storage.store_hotel_image(hotel.id, file)
    image = HotelImage(
        hotel_id=hotel.id,
        image_url=image_url,
        storage_key=storage_key,
        content_type=content_type,
        file_size=file_size,
        alt_text=alt_text.strip() if alt_text else None,
        is_cover=not any(item.is_cover for item in hotel.images),
        display_order=len(hotel.images),
    )
    try:
        db.add(image)
        hotel.images.append(image)
        _refresh_profile_completion(hotel)
        db.commit()
        db.refresh(image)
    except Exception:
        db.rollback()
        media_storage.delete_stored_file(storage_key)
        raise
    return HotelImageResponse.model_validate(image)


def set_partner_primary_image(db: Session, user: User, image_id: int) -> HotelImageResponse:
    hotel = _partner_hotel_or_404(db, user)
    image = hotel_repository.get_hotel_image(db, hotel.id, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel image not found")
    for item in hotel.images:
        item.is_cover = item.id == image.id
    db.commit()
    db.refresh(image)
    return HotelImageResponse.model_validate(image)


def reorder_partner_images(db: Session, user: User, data: HotelImageOrderUpdate) -> list[HotelImageResponse]:
    hotel = _partner_hotel_or_404(db, user)
    current_ids = {image.id for image in hotel.images}
    requested_ids = set(data.image_ids)
    if current_ids != requested_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Image order must include every image exactly once")
    by_id = {image.id: image for image in hotel.images}
    for order, image_id in enumerate(data.image_ids):
        by_id[image_id].display_order = order
    db.commit()
    return [HotelImageResponse.model_validate(by_id[image_id]) for image_id in data.image_ids]


def delete_partner_image(db: Session, user: User, image_id: int) -> None:
    hotel = _partner_hotel_or_404(db, user)
    image = hotel_repository.get_hotel_image(db, hotel.id, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hotel image not found")
    storage_key = image.storage_key
    db.delete(image)
    db.flush()
    _refresh_profile_completion(hotel)
    db.commit()
    media_storage.delete_stored_file(storage_key)


def submit_partner_verification(
    db: Session,
    user: User,
    data: VerificationSubmitRequest,
) -> HotelVerificationResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must create a hotel profile before submitting verification documents",
        )

    fee = payment_service.verification_fee_status(db, hotel.id)
    if fee.payment_status != PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pay the server-configured verification processing fee before submitting an application")

    # Atomic transaction: update/create verification with PENDING status, and set hotel status to PENDING.
    # A changes-request resubmission keeps the original payment valid.
    existing = hotel_verification_repository.get_verification_by_hotel_id(db, hotel.id)
    if existing and existing.verification_status in (VerificationStatus.APPROVED, VerificationStatus.REJECTED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This verification decision is final")
    verification = hotel_verification_repository.create_or_update_verification(db, hotel.id, data)
    if data.document_reference:
        if verification.document_storage_key != data.document_reference:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded verification document was not found")
    hotel.status = HotelStatus.PENDING
    db.commit()
    db.refresh(verification)
    result = HotelVerificationResponse.model_validate(verification)
    result.fee = fee
    return result


async def upload_partner_verification_document(db: Session, user: User, file: UploadFile) -> PrivateDocumentUploadResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No hotel found for this partner account")
    if payment_service.verification_fee_status(db, hotel.id).payment_status != PaymentStatus.PAID:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pay the verification processing fee before uploading documents")
    existing = hotel_verification_repository.get_verification_by_hotel_id(db, hotel.id)
    if existing is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Save the verification application before uploading a document")
    if existing.verification_status in (VerificationStatus.APPROVED, VerificationStatus.REJECTED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This verification decision is final")
    stored = await private_document_storage.store_verification_document(hotel.id, file)
    try:
        verification = db.scalar(select(HotelVerification).where(HotelVerification.id == existing.id).with_for_update())
        if verification is None or verification.hotel_id != hotel.id:
            raise HTTPException(status_code=404, detail="Verification application not found")
        previous_key = verification.document_storage_key
        verification.document_storage_key = stored.storage_key
        verification.document_original_name = stored.original_name
        verification.document_content_type = stored.content_type
        verification.document_size = stored.size
        verification.document_checksum_sha256 = stored.checksum_sha256
        verification.document_uploaded_by = user.id
        verification.document_uploaded_at = datetime.now(timezone.utc)
        audit_service.record(db, actor=user, action="HOTEL_VERIFICATION_DOCUMENT_UPLOADED", target_type="HOTEL_VERIFICATION", target_id=verification.id, reason="Partner uploaded private verification evidence", new_value={"content_type": stored.content_type, "size": stored.size, "replaced": bool(previous_key)})
        if previous_key and previous_key != stored.storage_key:
            private_document_lifecycle_service.enqueue(db, previous_key, reason="Hotel verification document replaced")
        db.commit()
    except Exception:
        db.rollback()
        try:
            private_document_storage.delete_document(stored.storage_key)
        except Exception:
            private_document_lifecycle_service.enqueue(db, stored.storage_key, reason="Verification upload database finalization failed")
            db.commit()
        raise
    return PrivateDocumentUploadResponse(document_reference=stored.storage_key, original_name=stored.original_name, content_type=stored.content_type, size=stored.size)


def get_partner_verification_document(db: Session, user: User, verification_id: int):
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    verification = hotel_verification_repository.get_verification_by_id(db, verification_id)
    if hotel is None or verification is None or verification.hotel_id != hotel.id or not verification.document_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification document not found")
    audit_service.record(db, actor=user, action="HOTEL_VERIFICATION_DOCUMENT_DOWNLOADED", target_type="HOTEL_VERIFICATION", target_id=verification.id, reason="Authorized partner document access")
    db.commit()
    return verification


def get_partner_verification(db: Session, user: User) -> HotelVerificationResponse:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hotel found for this partner account",
        )

    verification = hotel_verification_repository.get_verification_by_hotel_id(db, hotel.id)
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification documents have not yet been submitted for this hotel",
        )

    result = HotelVerificationResponse.model_validate(verification)
    result.fee = payment_service.verification_fee_status(db, hotel.id)
    return result

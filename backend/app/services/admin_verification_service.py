from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hotel import Hotel, HotelStatus
from app.models.hotel_verification import HotelVerification, VerificationStatus
from app.models.booking import Payment, PaymentPurpose, PaymentStatus
from app.models.communication import NotificationEventType
from app.models.user import User
from app.repositories import hotel_repository, hotel_verification_repository, user_repository
from app.schemas.hotel import HotelResponse
from app.schemas.hotel_verification import (
    AdminVerificationDetailResponse,
    AdminVerificationListItem,
    HotelVerificationResponse,
    ReviewActionType,
    VerificationReviewRequest,
)
from app.services import audit_service, notification_service, payment_service, refund_execution_service


def list_verification_requests(
    db: Session,
    status_filter: VerificationStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[AdminVerificationListItem]:
    verifications = hotel_verification_repository.list_verifications(
        db,
        status=status_filter,
        offset=offset,
        limit=limit,
    )
    items: list[AdminVerificationListItem] = []
    for ver in verifications:
        hotel = hotel_repository.get_hotel(db, ver.hotel_id)
        partner = user_repository.get_user_by_id(db, hotel.partner_id) if hotel and hotel.partner_id else None
        items.append(
            AdminVerificationListItem(
                id=ver.id,
                hotel_id=ver.hotel_id,
                hotel_name=hotel.name if hotel else "Unknown Hotel",
                hotel_slug=hotel.slug if hotel else "",
                hotel_city=hotel.city if hotel else "",
                hotel_state=hotel.state if hotel else "",
                partner_id=partner.id if partner else None,
                partner_name=partner.full_name if partner else None,
                partner_email=partner.email if partner else None,
                business_name=ver.business_name,
                business_type=ver.business_type,
                verification_status=ver.verification_status,
                payment_status=payment_service.verification_fee_status(db, ver.hotel_id).payment_status,
                submitted_at=ver.submitted_at,
                reviewed_at=ver.reviewed_at,
                created_at=ver.created_at,
            )
        )
    return items


def get_verification_detail(db: Session, verification_id: int) -> AdminVerificationDetailResponse:
    verification = db.scalar(select(HotelVerification).where(HotelVerification.id == verification_id).with_for_update())
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel verification request not found",
        )

    hotel = db.scalar(select(Hotel).where(Hotel.id == verification.hotel_id).with_for_update())
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated hotel record not found",
        )

    partner = user_repository.get_user_by_id(db, hotel.partner_id) if hotel.partner_id else None
    partner_dict = (
        {
            "id": partner.id,
            "full_name": partner.full_name,
            "email": partner.email,
            "phone": partner.phone,
            "created_at": partner.created_at.isoformat(),
        }
        if partner
        else None
    )

    verification_response = HotelVerificationResponse.model_validate(verification)
    verification_response.fee = payment_service.verification_fee_status(db, hotel.id)
    return AdminVerificationDetailResponse(
        verification=verification_response,
        hotel=HotelResponse.model_validate(hotel),
        partner=partner_dict,
    )


def review_verification(
    db: Session,
    admin_user: User,
    verification_id: int,
    review_data: VerificationReviewRequest,
) -> HotelVerificationResponse:
    from app.services import admin_control_service
    verification = db.scalar(select(HotelVerification).where(HotelVerification.id == verification_id).with_for_update())
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel verification request not found",
        )

    hotel = hotel_repository.get_hotel(db, verification.hotel_id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated hotel record not found",
        )

    fee = payment_service.verification_fee_status(db, hotel.id)
    if fee.payment_status != PaymentStatus.PAID and not (
        review_data.action == ReviewActionType.REJECT and verification.verification_status == VerificationStatus.REJECTED
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A verified verification-fee payment is required before Admin review")

    if verification.verification_status == VerificationStatus.REJECTED:
        # A retried rejection is idempotent, but also repairs the narrow case
        # where rejection committed before its refund instruction was created.
        if review_data.action != ReviewActionType.REJECT:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A final rejection cannot be changed")
        payment = db.scalar(select(Payment).where(Payment.id == fee.payment_id, Payment.purpose == PaymentPurpose.VERIFICATION_FEE)) if fee.payment_id else None
        if payment and payment.status in (PaymentStatus.PAID, PaymentStatus.REFUND_PENDING):
            refund = refund_execution_service.create_verification_instruction(db, verification, payment)
            db.commit()
            refund_execution_service.submit_refund(db, refund.id, admin=admin_user, reason="Final verification rejection refund")
        result = HotelVerificationResponse.model_validate(verification)
        result.fee = payment_service.verification_fee_status(db, hotel.id)
        return result

    now = datetime.now(timezone.utc)
    previous = {"verification_status": verification.verification_status.value, "hotel_status": hotel.status.value}
    verification.reviewed_by = admin_user.id
    verification.reviewed_at = now
    new_hotel_status = hotel.status

    if review_data.action == ReviewActionType.APPROVE:
        verification.verification_status = VerificationStatus.APPROVED
        verification.rejection_reason = None
        if review_data.admin_notes:
            verification.admin_notes = review_data.admin_notes
        new_hotel_status = HotelStatus.ACTIVE

    elif review_data.action == ReviewActionType.REJECT:
        verification.verification_status = VerificationStatus.REJECTED
        verification.rejection_reason = review_data.rejection_reason
        verification.admin_notes = review_data.admin_notes
        new_hotel_status = HotelStatus.DRAFT

    elif review_data.action in (ReviewActionType.REQUEST_INFO, ReviewActionType.REQUEST_CHANGES):
        verification.verification_status = VerificationStatus.NEEDS_CHANGES if review_data.action == ReviewActionType.REQUEST_CHANGES else VerificationStatus.ADDITIONAL_INFO_REQUIRED
        verification.admin_notes = review_data.admin_notes
        new_hotel_status = HotelStatus.DRAFT

    reason = review_data.rejection_reason or review_data.admin_notes or f"Verification {review_data.action.value.lower()}"
    admin_control_service.change_hotel_status(
        db,
        admin_user,
        hotel,
        new_hotel_status,
        reason=reason,
        action="HOTEL_VERIFICATION_REVIEWED",
        target_type="HOTEL_VERIFICATION",
        target_id=verification.id,
        previous_value=previous,
        new_value={"verification_status": verification.verification_status.value, "hotel_status": new_hotel_status.value, "decision": review_data.action.value},
    )

    if hotel.partner_id:
        event_type = {
            ReviewActionType.APPROVE: NotificationEventType.VERIFICATION_APPROVED,
            ReviewActionType.REJECT: NotificationEventType.VERIFICATION_REJECTED,
            ReviewActionType.REQUEST_INFO: NotificationEventType.VERIFICATION_CHANGES_REQUESTED,
            ReviewActionType.REQUEST_CHANGES: NotificationEventType.VERIFICATION_CHANGES_REQUESTED,
        }[review_data.action]
        notification_service.create(
            db,
            recipient_user_id=hotel.partner_id,
            event_type=event_type,
            dedupe_key=f"verification:{verification.id}:{verification.verification_status.value}:{verification.reviewed_at.isoformat()}",
            title={ReviewActionType.APPROVE: "Verification approved", ReviewActionType.REJECT: "Verification rejected", ReviewActionType.REQUEST_INFO: "Verification changes requested", ReviewActionType.REQUEST_CHANGES: "Verification changes requested"}[review_data.action],
            body=reason,
            data={"hotel_id": hotel.id, "verification_id": verification.id, "status": verification.verification_status.value},
        )

    refund_id = None
    if review_data.action == ReviewActionType.REJECT:
        payment = db.scalar(select(Payment).where(Payment.id == fee.payment_id, Payment.purpose == PaymentPurpose.VERIFICATION_FEE).with_for_update())
        if payment is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verification payment record is missing")
        refund = refund_execution_service.create_verification_instruction(db, verification, payment)
        refund_id = refund.id
        audit_service.record(
            db,
            actor=admin_user,
            action="VERIFICATION_REFUND_TRIGGERED",
            target_type="REFUND",
            target_id=refund.id,
            reason=review_data.rejection_reason or "Final verification rejection",
            previous_value=None,
            new_value={"verification_id": verification.id, "payment_id": payment.id, "amount": str(payment.amount), "currency": payment.currency},
        )

    db.commit()
    db.refresh(verification)
    if refund_id is not None:
        refund_execution_service.submit_refund(db, refund_id, admin=admin_user, reason="Final verification rejection refund")
    result = HotelVerificationResponse.model_validate(verification)
    result.fee = payment_service.verification_fee_status(db, hotel.id)
    return result


def get_verification_document(db: Session, admin: User, verification_id: int):
    verification = hotel_verification_repository.get_verification_by_id(db, verification_id)
    if verification is None or not verification.document_storage_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification document not found")
    audit_service.record(db, actor=admin, action="HOTEL_VERIFICATION_DOCUMENT_VIEWED", target_type="HOTEL_VERIFICATION", target_id=verification.id, reason="Authorized admin document review", previous_value=None, new_value=None)
    db.commit()
    return verification

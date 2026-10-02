from datetime import datetime, timezone
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.hotel_verification import HotelVerification, VerificationStatus
from app.schemas.hotel_verification import VerificationSubmitRequest


def get_verification_by_hotel_id(db: Session, hotel_id: int) -> HotelVerification | None:
    query = select(HotelVerification).where(HotelVerification.hotel_id == hotel_id)
    return db.scalars(query).first()


def get_verification_by_id(db: Session, verification_id: int) -> HotelVerification | None:
    query = select(HotelVerification).where(HotelVerification.id == verification_id)
    return db.scalars(query).first()


def create_or_update_verification(
    db: Session,
    hotel_id: int,
    data: VerificationSubmitRequest,
) -> HotelVerification:
    verification = get_verification_by_hotel_id(db, hotel_id)
    now = datetime.now(timezone.utc)
    if verification is None:
        verification = HotelVerification(
            hotel_id=hotel_id,
            business_name=data.business_name,
            business_type=data.business_type,
            gstin=data.gstin,
            pan=data.pan,
            bank_account_number=data.bank_account_number,
            bank_ifsc=data.bank_ifsc,
            bank_name=data.bank_name,
            bank_beneficiary_name=data.bank_beneficiary_name,
            document_proof_type=data.document_proof_type,
            document_proof_url=None,
            verification_status=VerificationStatus.PENDING,
            submitted_at=now,
        )
        db.add(verification)
    else:
        verification.business_name = data.business_name
        verification.business_type = data.business_type
        verification.gstin = data.gstin
        verification.pan = data.pan
        verification.bank_account_number = data.bank_account_number
        verification.bank_ifsc = data.bank_ifsc
        verification.bank_name = data.bank_name
        verification.bank_beneficiary_name = data.bank_beneficiary_name
        verification.document_proof_type = data.document_proof_type
        verification.document_proof_url = None
        verification.verification_status = VerificationStatus.PENDING
        verification.submitted_at = now
        verification.rejection_reason = None
        verification.admin_notes = None

    db.flush()
    db.refresh(verification)
    return verification


def list_verifications(
    db: Session,
    status: VerificationStatus | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[HotelVerification]:
    query: Select = select(HotelVerification).order_by(HotelVerification.created_at.desc())
    if status is not None:
        query = query.where(HotelVerification.verification_status == status)
    query = query.offset(offset).limit(limit)
    return list(db.scalars(query).all())


def count_verifications(
    db: Session,
    status: VerificationStatus | None = None,
) -> int:
    query = select(func.count(HotelVerification.id))
    if status is not None:
        query = query.where(HotelVerification.verification_status == status)
    return db.scalar(query) or 0

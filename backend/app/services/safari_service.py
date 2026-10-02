from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import Payment, PaymentPurpose, PaymentReconciliationStatus, PaymentStatus, Refund
from app.models.communication import NotificationEventType
from app.models.safari import Safari, SafariAlternative, SafariDocument, SafariDocumentKind, SafariOperationalNotice, SafariRequest, SafariRequestStatus, SafariTraveller
from app.models.user import User
from app.schemas.safari import AvailabilityDecision, AvailabilityRequestCreate, ConfirmationInput, PricingInput, SafariConfigurationUpdate, SafariDocumentResponse, SafariOperationalNoticeCreate, SafariOperationalNoticeResponse, SafariOperationalNoticeUpdate, SafariPublic, SafariRequestResponse, TravellerResponse, TravellerSubmission
from app.services import audit_service, notification_service, payment_provider, private_document_lifecycle_service, private_document_storage, refund_execution_service


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _query():
    return select(SafariRequest).execution_options(populate_existing=True).options(
        selectinload(SafariRequest.safari).selectinload(Safari.district),
        selectinload(SafariRequest.safari).selectinload(Safari.destination),
        selectinload(SafariRequest.alternatives),
        selectinload(SafariRequest.travellers).selectinload(SafariTraveller.documents),
        selectinload(SafariRequest.documents),
    )


def _public_query():
    return select(Safari).options(selectinload(Safari.district), selectinload(Safari.destination))


def _active_notices(db: Session, safari_id: int) -> list[SafariOperationalNoticeResponse]:
    now = datetime.now(timezone.utc)
    query = select(SafariOperationalNotice).where(
        SafariOperationalNotice.is_active.is_(True),
        or_(SafariOperationalNotice.safari_id.is_(None), SafariOperationalNotice.safari_id == safari_id),
        or_(SafariOperationalNotice.effective_from.is_(None), SafariOperationalNotice.effective_from <= now),
        or_(SafariOperationalNotice.effective_until.is_(None), SafariOperationalNotice.effective_until > now),
    ).order_by(SafariOperationalNotice.severity.desc(), SafariOperationalNotice.created_at.desc())
    return [SafariOperationalNoticeResponse.model_validate(value) for value in db.scalars(query)]


def _public_safari(db: Session, item: Safari) -> SafariPublic:
    district_slug = item.district.slug if item.district else None
    destination_slug = item.destination.slug if item.destination else None
    destination_path = (
        f"/destinations/{district_slug}/{destination_slug}"
        if district_slug and destination_slug
        else f"/destinations/{district_slug}" if district_slug else None
    )
    hotel_destination_filter = (
        f"{district_slug}/{destination_slug}"
        if district_slug and destination_slug
        else district_slug
    )
    return SafariPublic(
        id=item.id, name=item.name, slug=item.slug, short_description=item.short_description,
        district_id=item.district_id, destination_id=item.destination_id,
        district_name=item.district.name if item.district else None, district_slug=district_slug,
        destination_name=item.destination.name if item.destination else None, destination_slug=destination_slug,
        destination_path=destination_path, hotel_destination_filter=hotel_destination_filter,
        booking_categories=item.booking_categories, vehicle_options=item.vehicle_options,
        shifts=item.shifts, zones=item.zones, gates=item.gates,
        traveller_requirements=item.traveller_requirements,
        official_reference_required=item.official_reference_required,
        official_contact_required=item.official_contact_required,
        official_document_required=item.official_document_required,
        source_url=item.source_url, last_verified_at=item.last_verified_at,
        operational_notices=_active_notices(db, item.id),
    )


def list_public(db: Session) -> list[SafariPublic]:
    items = db.scalars(_public_query().where(Safari.is_active.is_(True), Safari.is_public.is_(True)).order_by(Safari.name))
    return [_public_safari(db, item) for item in items]


def get_public(db: Session, slug: str) -> SafariPublic:
    item = db.scalar(_public_query().where(Safari.slug == slug, Safari.is_active.is_(True), Safari.is_public.is_(True)))
    if item is None: raise HTTPException(status_code=404, detail="Safari not found")
    return _public_safari(db, item)


def _payment(db: Session, request_id: int) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.safari_request_id == request_id).order_by(Payment.id.desc()))


def _refund(db: Session, request_id: int) -> Refund | None:
    return db.scalar(select(Refund).where(Refund.safari_request_id == request_id).order_by(Refund.id.desc()))


def response(db: Session, item: SafariRequest) -> SafariRequestResponse:
    payment, refund = _payment(db, item.id), _refund(db, item.id)
    travellers = [TravellerResponse(id=t.id, position=t.position, details=json.loads(t.details_encrypted), documents=[SafariDocumentResponse.model_validate(d) for d in t.documents]) for t in sorted(item.travellers, key=lambda value: value.position)]
    confirmations = [SafariDocumentResponse.model_validate(d) for d in item.documents if d.kind == SafariDocumentKind.CONFIRMATION]
    return SafariRequestResponse(
        id=item.id, request_reference=item.request_reference, safari=_public_safari(db, item.safari),
        preferred_date=item.preferred_date, preferred_shift=item.preferred_shift,
        preferred_booking_category=item.preferred_booking_category, preferred_vehicle_option=item.preferred_vehicle_option,
        visitor_count=item.visitor_count,
        alternate_preference=item.alternate_preference, status=item.status, availability_result=item.availability_result,
        alternatives=item.alternatives, selected_alternative_id=item.selected_alternative_id,
        target_response_at=item.target_response_at, responded_at=item.responded_at,
        overdue=item.responded_at is None and _aware(item.target_response_at) < datetime.now(timezone.utc),
        payable_amount=item.payable_amount, currency=item.currency, price_breakdown=item.price_breakdown,
        payment_status=payment.status if payment else PaymentStatus.NOT_STARTED,
        payment_reconciliation_status=payment.reconciliation_status if payment else None,
        refund_status=refund.status if refund else None, travellers=travellers, confirmation_documents=confirmations,
        external_booking_reference=item.external_booking_reference, confirmed_date=item.confirmed_date,
        confirmed_shift=item.confirmed_shift, confirmed_zone=item.confirmed_zone, confirmed_gate=item.confirmed_gate,
        confirmed_booking_category=item.confirmed_booking_category, confirmed_vehicle_option=item.confirmed_vehicle_option,
        official_booking_contact_masked=_mask_contact(item.official_booking_contact), operator_confirmed_at=item.operator_confirmed_at,
        reporting_instructions=item.reporting_instructions, final_amount=item.final_amount,
        failure_reason=item.failure_reason, created_at=item.created_at, updated_at=item.updated_at,
    )


def _notify(db: Session, item: SafariRequest, event: NotificationEventType, suffix: str, title: str, body: str) -> None:
    notification_service.create(db, recipient_user_id=item.customer_id, event_type=event,
        dedupe_key=f"safari:{item.id}:{suffix}", title=title, body=body,
        data={"safari_request_id": item.id, "request_reference": item.request_reference, "safari_id": item.safari_id})


def create_request(db: Session, user: User, safari_slug: str, data: AvailabilityRequestCreate) -> SafariRequestResponse:
    safari = db.scalar(_public_query().where(Safari.slug == safari_slug, Safari.is_active.is_(True), Safari.is_public.is_(True)))
    if safari is None: raise HTTPException(status_code=404, detail="Safari not found")
    if data.preferred_date < date.today(): raise HTTPException(status_code=422, detail="Preferred date cannot be in the past")
    if safari.shifts and data.preferred_shift not in safari.shifts: raise HTTPException(status_code=422, detail="Unsupported shift for this safari")
    _validate_option(safari.booking_categories, data.preferred_booking_category, "booking category")
    _validate_option(safari.vehicle_options, data.preferred_vehicle_option, "vehicle option")
    item = SafariRequest(request_reference=f"SAF-{uuid.uuid4().hex[:12].upper()}", safari_id=safari.id, customer_id=user.id,
        preferred_date=data.preferred_date, preferred_shift=data.preferred_shift,
        preferred_booking_category=data.preferred_booking_category, preferred_vehicle_option=data.preferred_vehicle_option,
        visitor_count=data.visitor_count,
        alternate_preference=data.alternate_preference, target_response_at=datetime.now(timezone.utc) + timedelta(minutes=settings.SAFARI_RESPONSE_TARGET_MINUTES))
    db.add(item); db.flush()
    _notify(db, item, NotificationEventType.SAFARI_REQUEST_RECEIVED, "received", "Safari request received", "Maharashtra Tourist Places received your availability request. The response target is operational and does not guarantee availability.")
    db.commit(); db.expire_all(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def _owned(db: Session, user: User, request_id: int, lock: bool = False) -> SafariRequest:
    query = _query().where(SafariRequest.id == request_id, SafariRequest.customer_id == user.id)
    if lock: query = query.with_for_update()
    item = db.scalar(query)
    if item is None: raise HTTPException(status_code=404, detail="Safari request not found")
    return item


def list_customer(db: Session, user: User) -> list[SafariRequestResponse]:
    return [response(db, item) for item in db.scalars(_query().where(SafariRequest.customer_id == user.id).order_by(SafariRequest.created_at.desc()))]


def get_customer(db: Session, user: User, request_id: int) -> SafariRequestResponse:
    return response(db, _owned(db, user, request_id))


def list_admin(db: Session, status_filter: SafariRequestStatus | None, overdue_only: bool) -> list[SafariRequestResponse]:
    query = _query()
    if status_filter: query = query.where(SafariRequest.status == status_filter)
    if overdue_only: query = query.where(SafariRequest.responded_at.is_(None), SafariRequest.target_response_at < datetime.now(timezone.utc))
    return [response(db, item) for item in db.scalars(query.order_by(SafariRequest.created_at))]


def availability_decision(db: Session, admin: User, request_id: int, data: AvailabilityDecision) -> SafariRequestResponse:
    item = db.scalar(_query().where(SafariRequest.id == request_id).with_for_update())
    if item is None: raise HTTPException(status_code=404, detail="Safari request not found")
    previous = item.status
    if data.action == "START_CHECK":
        if item.status == SafariRequestStatus.CHECKING_AVAILABILITY: return response(db, item)
        if item.status != SafariRequestStatus.AVAILABILITY_REQUESTED: raise HTTPException(status_code=409, detail="Request is not awaiting an availability check")
        item.status = SafariRequestStatus.CHECKING_AVAILABILITY
    elif data.action in ("MARK_AVAILABLE", "MARK_UNAVAILABLE"):
        target = SafariRequestStatus.AWAITING_TRAVELLER_DETAILS if data.action == "MARK_AVAILABLE" else SafariRequestStatus.NOT_AVAILABLE
        if item.status == target: return response(db, item)
        if item.status not in (SafariRequestStatus.AVAILABILITY_REQUESTED, SafariRequestStatus.CHECKING_AVAILABILITY): raise HTTPException(status_code=409, detail="Availability has already been decided")
        item.status, item.availability_result, item.responded_at = target, "AVAILABLE" if data.action == "MARK_AVAILABLE" else "NOT_AVAILABLE", datetime.now(timezone.utc)
        for alt in data.alternatives:
            _validate_option(item.safari.booking_categories, alt.booking_category, "booking category")
            _validate_option(item.safari.vehicle_options, alt.vehicle_option, "vehicle option")
            item.alternatives.append(SafariAlternative(**alt.model_dump()))
        event = NotificationEventType.SAFARI_DETAILS_REQUIRED if data.action == "MARK_AVAILABLE" else NotificationEventType.SAFARI_AVAILABILITY_UPDATE
        _notify(db, item, event, item.availability_result.lower(), "Safari availability update", "Availability was confirmed. Traveller details are now required." if data.action == "MARK_AVAILABLE" else "The requested safari option is unavailable. Review any alternatives offered in your account.")
    else: raise HTTPException(status_code=422, detail="Unknown action")
    item.internal_notes = data.internal_notes or item.internal_notes
    audit_service.record(db, actor=admin, action=f"SAFARI_{data.action}", target_type="safari_request", target_id=item.id, reason=data.reason,
        previous_value={"status": previous.value}, new_value={"status": item.status.value, "alternative_count": len(item.alternatives)})
    db.commit(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def select_alternative(db: Session, user: User, request_id: int, alternative_id: int) -> SafariRequestResponse:
    item = _owned(db, user, request_id, lock=True)
    alternative = next((value for value in item.alternatives if value.id == alternative_id), None)
    if alternative is None: raise HTTPException(status_code=404, detail="Alternative not found")
    if item.status == SafariRequestStatus.AWAITING_TRAVELLER_DETAILS and item.selected_alternative_id == alternative_id: return response(db, item)
    if item.status != SafariRequestStatus.NOT_AVAILABLE: raise HTTPException(status_code=409, detail="An alternative cannot be selected now")
    item.selected_alternative_id, item.availability_result, item.status = alternative.id, "ALTERNATIVE_SELECTED", SafariRequestStatus.AWAITING_TRAVELLER_DETAILS
    db.commit(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def save_travellers(db: Session, user: User, request_id: int, data: TravellerSubmission) -> SafariRequestResponse:
    item = _owned(db, user, request_id, lock=True)
    if item.status != SafariRequestStatus.AWAITING_TRAVELLER_DETAILS: raise HTTPException(status_code=409, detail="Traveller details are not currently accepted")
    if len(data.travellers) != item.visitor_count: raise HTTPException(status_code=422, detail="Traveller count must match the availability request")
    if any(value.documents for value in item.travellers): raise HTTPException(status_code=409, detail="Traveller details with uploaded documents cannot be replaced")
    required = [str(field.get("key")) for field in item.safari.traveller_requirements.get("fields", []) if isinstance(field, dict) and field.get("required")]
    for traveller in data.travellers:
        missing = [key for key in required if not traveller.details.get(key)]
        if missing: raise HTTPException(status_code=422, detail=f"Missing configured traveller fields: {', '.join(missing)}")
    db.execute(delete(SafariTraveller).where(SafariTraveller.request_id == item.id))
    for position, traveller in enumerate(data.travellers, 1): db.add(SafariTraveller(request_id=item.id, position=position, details_encrypted=json.dumps(traveller.details, separators=(",", ":"))))
    db.commit(); db.expire_all(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


async def upload_document(db: Session, actor: User, request_id: int, traveller_id: int | None, document_type: str, kind: SafariDocumentKind, file: UploadFile, *, admin: bool = False) -> SafariDocument:
    item = db.scalar(_query().where(SafariRequest.id == request_id))
    if item is None or (not admin and item.customer_id != actor.id): raise HTTPException(status_code=404, detail="Safari request not found")
    if kind == SafariDocumentKind.TRAVELLER:
        traveller = next((value for value in item.travellers if value.id == traveller_id), None)
        if traveller is None: raise HTTPException(status_code=404, detail="Traveller not found")
        if item.status != SafariRequestStatus.AWAITING_TRAVELLER_DETAILS: raise HTTPException(status_code=409, detail="Traveller documents are not currently accepted")
    elif not admin or item.status not in (SafariRequestStatus.BOOKING_IN_PROGRESS, SafariRequestStatus.CONFIRMED):
        raise HTTPException(status_code=409, detail="Confirmation documents are not currently accepted")
    stored = await private_document_storage.store_safari_document(item.id, "confirmation" if kind == SafariDocumentKind.CONFIRMATION else "traveller", file)
    try:
        item = db.scalar(_query().where(SafariRequest.id == request_id).with_for_update())
        if item is None or (not admin and item.customer_id != actor.id):
            raise HTTPException(status_code=404, detail="Safari request not found")
        normalized_type = document_type[:100]
        if kind == SafariDocumentKind.TRAVELLER:
            traveller = next((value for value in item.travellers if value.id == traveller_id), None)
            if traveller is None or item.status != SafariRequestStatus.AWAITING_TRAVELLER_DETAILS:
                raise HTTPException(status_code=409, detail="Traveller documents are not currently accepted")
            previous = next((doc for doc in traveller.documents if doc.kind == kind and doc.document_type == normalized_type), None)
        else:
            if not admin or item.status not in (SafariRequestStatus.BOOKING_IN_PROGRESS, SafariRequestStatus.CONFIRMED):
                raise HTTPException(status_code=409, detail="Confirmation documents are not currently accepted")
            previous = next((doc for doc in item.documents if doc.kind == kind and doc.document_type == normalized_type), None)
        document = SafariDocument(request_id=item.id, traveller_id=traveller_id, kind=kind, document_type=normalized_type, storage_key=stored.storage_key, original_name=stored.original_name, content_type=stored.content_type, size=stored.size, checksum_sha256=stored.checksum_sha256, uploaded_by=actor.id)
        db.add(document)
        db.flush()
        audit_service.record(db, actor=actor, action="SAFARI_PRIVATE_DOCUMENT_UPLOADED", target_type="SAFARI_DOCUMENT", target_id=document.id, reason="Authorized Safari document upload", new_value={"request_id": item.id, "kind": kind.value, "content_type": stored.content_type, "size": stored.size, "replaced": bool(previous)})
        if previous:
            private_document_lifecycle_service.enqueue(db, previous.storage_key, reason="Safari document replaced")
            db.delete(previous)
        db.commit()
        db.refresh(document)
        return document
    except Exception:
        db.rollback()
        try:
            private_document_storage.delete_document(stored.storage_key)
        except Exception:
            private_document_lifecycle_service.enqueue(db, stored.storage_key, reason="Safari upload database finalization failed")
            db.commit()
        raise


def submit_travellers(db: Session, user: User, request_id: int) -> SafariRequestResponse:
    item = _owned(db, user, request_id, lock=True)
    if item.status in (SafariRequestStatus.DETAILS_SUBMITTED, SafariRequestStatus.PAYMENT_PENDING): return response(db, item)
    if item.status != SafariRequestStatus.AWAITING_TRAVELLER_DETAILS or len(item.travellers) != item.visitor_count: raise HTTPException(status_code=409, detail="Complete all traveller details first")
    required_docs = [str(value.get("type")) for value in item.safari.traveller_requirements.get("documents", []) if isinstance(value, dict) and value.get("required")]
    for traveller in item.travellers:
        present = {doc.document_type for doc in traveller.documents}
        if any(doc_type not in present for doc_type in required_docs): raise HTTPException(status_code=409, detail="Configured traveller documents are incomplete")
    item.status = SafariRequestStatus.PAYMENT_PENDING if item.payable_amount else SafariRequestStatus.DETAILS_SUBMITTED
    if item.status == SafariRequestStatus.PAYMENT_PENDING: _notify(db, item, NotificationEventType.SAFARI_PAYMENT_REQUIRED, "payment-required", "Safari payment required", "Traveller details are complete. Review the authoritative price breakdown before payment.")
    db.commit(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def set_pricing(db: Session, admin: User, request_id: int, data: PricingInput) -> SafariRequestResponse:
    item = db.scalar(_query().where(SafariRequest.id == request_id).with_for_update())
    if item is None: raise HTTPException(status_code=404, detail="Safari request not found")
    if item.status not in (SafariRequestStatus.AWAITING_TRAVELLER_DETAILS, SafariRequestStatus.DETAILS_SUBMITTED, SafariRequestStatus.PAYMENT_PENDING): raise HTTPException(status_code=409, detail="Pricing cannot be set in this state")
    existing = _payment(db, item.id)
    if existing: raise HTTPException(status_code=409, detail="Pricing cannot change after a payment order exists")
    previous = {"amount": str(item.payable_amount) if item.payable_amount else None, "currency": item.currency}
    item.payable_amount, item.currency, item.price_breakdown = data.amount, data.currency.upper(), data.breakdown
    if item.status == SafariRequestStatus.DETAILS_SUBMITTED:
        item.status = SafariRequestStatus.PAYMENT_PENDING
        _notify(db, item, NotificationEventType.SAFARI_PAYMENT_REQUIRED, "payment-required", "Safari payment required", "Your final safari price is ready. Review the breakdown before payment.")
    audit_service.record(db, actor=admin, action="SAFARI_PRICING_CONFIRMED", target_type="safari_request", target_id=item.id, reason=data.reason, previous_value=previous, new_value={"amount": str(data.amount), "currency": data.currency.upper()})
    db.commit(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def create_payment_order(db: Session, user: User, request_id: int) -> Payment:
    if settings.PAYMENT_MODE == "disabled": raise HTTPException(status_code=503, detail="Payments are disabled")
    item = _owned(db, user, request_id, lock=True)
    if item.status != SafariRequestStatus.PAYMENT_PENDING or not item.payable_amount or not item.currency: raise HTTPException(status_code=409, detail="Safari request is not eligible for payment")
    existing = _payment(db, item.id)
    if existing and existing.status in (PaymentStatus.PENDING, PaymentStatus.PAID): return existing
    provider = payment_provider.configured_provider(); order = provider.create_order(amount=item.payable_amount, currency=item.currency, booking_reference=item.request_reference)
    payment = Payment(safari_request_id=item.id, purpose=PaymentPurpose.SAFARI_BOOKING, provider=provider.name, provider_order_id=order.provider_order_id, amount=item.payable_amount, currency=item.currency, status=PaymentStatus.PENDING)
    db.add(payment); db.commit(); db.refresh(payment); return payment


def payment_succeeded(db: Session, payment: Payment) -> None:
    item = db.get(SafariRequest, payment.safari_request_id) if payment.safari_request_id else None
    if item is None: return
    if item.status == SafariRequestStatus.PAYMENT_PENDING: item.status = SafariRequestStatus.BOOKING_IN_PROGRESS
    payment.reconciliation_status, payment.reconciliation_resolved_at = PaymentReconciliationStatus.RESOLVED, datetime.now(timezone.utc)
    _notify(db, item, NotificationEventType.SAFARI_PAYMENT_RECEIVED, f"payment:{payment.id}", "Safari payment received", "Payment was received. Maharashtra Tourist Places is now manually completing the external safari booking; payment is not confirmation.")


def confirm(db: Session, admin: User, request_id: int, data: ConfirmationInput) -> SafariRequestResponse:
    item = db.scalar(_query().where(SafariRequest.id == request_id).with_for_update())
    if item is None: raise HTTPException(status_code=404, detail="Safari request not found")
    if item.status == SafariRequestStatus.CONFIRMED: return response(db, item)
    if item.status != SafariRequestStatus.BOOKING_IN_PROGRESS: raise HTTPException(status_code=409, detail="Safari booking is not in progress")
    if item.payable_amount != data.final_amount: raise HTTPException(status_code=422, detail="Final amount must match the paid authoritative amount")
    if item.safari.official_reference_required and not data.booking_reference: raise HTTPException(status_code=422, detail="Official booking reference is required for this safari")
    if item.safari.official_contact_required and not data.official_booking_contact: raise HTTPException(status_code=422, detail="Official booking contact is required for this safari")
    if item.safari.official_document_required and not any(document.kind == SafariDocumentKind.CONFIRMATION for document in item.documents):
        raise HTTPException(status_code=409, detail="Official ticket or permit document is required before confirmation")
    _validate_option(item.safari.booking_categories, data.booking_category, "booking category")
    _validate_option(item.safari.vehicle_options, data.vehicle_option, "vehicle option")
    item.external_booking_reference, item.confirmed_date, item.confirmed_shift = data.booking_reference, data.safari_date, data.shift
    item.confirmed_zone, item.confirmed_gate, item.reporting_instructions, item.final_amount = data.zone, data.gate, data.reporting_instructions, data.final_amount
    item.confirmed_booking_category, item.confirmed_vehicle_option = data.booking_category, data.vehicle_option
    item.official_booking_contact, item.operator_confirmed_at = data.official_booking_contact, datetime.now(timezone.utc)
    item.status = SafariRequestStatus.CONFIRMED
    audit_service.record(db, actor=admin, action="SAFARI_BOOKING_CONFIRMED", target_type="safari_request", target_id=item.id, reason=data.reason, previous_value={"status": SafariRequestStatus.BOOKING_IN_PROGRESS.value}, new_value={"status": item.status.value, "booking_reference_recorded": bool(data.booking_reference), "ticket_recorded": bool(item.documents), "booking_category": data.booking_category, "vehicle_option": data.vehicle_option})
    _notify(db, item, NotificationEventType.SAFARI_BOOKING_CONFIRMED, "confirmed", "Safari booking confirmed", "Your safari booking is confirmed. Secure confirmation details and documents are available in your account.")
    db.commit(); item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def fail_booking(db: Session, admin: User, request_id: int, reason: str) -> SafariRequestResponse:
    item = db.scalar(_query().where(SafariRequest.id == request_id).with_for_update())
    if item is None: raise HTTPException(status_code=404, detail="Safari request not found")
    if item.status == SafariRequestStatus.BOOKING_FAILED: return response(db, item)
    if item.status != SafariRequestStatus.BOOKING_IN_PROGRESS: raise HTTPException(status_code=409, detail="Safari booking is not in progress")
    payment = _payment(db, item.id)
    item.status, item.failure_reason = SafariRequestStatus.BOOKING_FAILED, reason
    audit_service.record(db, actor=admin, action="SAFARI_BOOKING_FAILED", target_type="safari_request", target_id=item.id, reason=reason, previous_value={"status": SafariRequestStatus.BOOKING_IN_PROGRESS.value}, new_value={"status": item.status.value, "refund_required": bool(payment and payment.status == PaymentStatus.PAID)})
    _notify(db, item, NotificationEventType.SAFARI_BOOKING_FAILED, "failed", "Safari booking could not be completed", "The external safari booking could not be completed. Any captured payment is being handled through Maharashtra Tourist Places reconciliation.")
    if payment and payment.status == PaymentStatus.PAID:
        payment.reconciliation_status = PaymentReconciliationStatus.REFUND_REQUIRED
        refund = refund_execution_service.create_safari_instruction(db, item, payment)
        db.commit()
        refund_execution_service.submit_refund(db, refund.id, admin=admin, reason="Safari external booking failed")
    else: db.commit()
    item = db.scalar(_query().where(SafariRequest.id == item.id)); return response(db, item)


def document_path(db: Session, actor: User, request_id: int, document_id: int, *, admin: bool = False):
    item = db.get(SafariRequest, request_id); document = db.get(SafariDocument, document_id)
    if item is None or document is None or document.request_id != item.id or (not admin and item.customer_id != actor.id): raise HTTPException(status_code=404, detail="Safari document not found")
    audit_service.record(db, actor=actor, action="SAFARI_PRIVATE_DOCUMENT_DOWNLOADED", target_type="SAFARI_DOCUMENT", target_id=document.id, reason="Authorized Safari document access", new_value={"request_id": item.id, "kind": document.kind.value})
    db.commit()
    return document


def _configured_codes(options: list[dict[str, object]]) -> set[str]:
    return {str(value.get("code")) for value in options if isinstance(value, dict) and value.get("code")}


def _validate_option(options: list[dict[str, object]], selected: str | None, label: str) -> None:
    codes = _configured_codes(options)
    if selected and selected not in codes: raise HTTPException(status_code=422, detail=f"Unsupported {label} for this safari")
    if codes and not selected: raise HTTPException(status_code=422, detail=f"Select a configured {label} for this safari")


def _mask_contact(value: str | None) -> str | None:
    if not value: return None
    visible = value[-4:]
    return f"{'•' * max(0, len(value) - 4)}{visible}"


def update_configuration(db: Session, admin: User, safari_id: int, data: SafariConfigurationUpdate) -> SafariPublic:
    item = db.scalar(_public_query().where(Safari.id == safari_id).with_for_update())
    if item is None: raise HTTPException(status_code=404, detail="Safari not found")
    changes = data.model_dump(exclude={"reason"}, exclude_unset=True)
    audit_changes = data.model_dump(exclude={"reason"}, exclude_unset=True, mode="json")
    previous = {key: value.isoformat() if isinstance((value := getattr(item, key)), datetime) else value for key in changes}
    for key, value in changes.items(): setattr(item, key, value)
    audit_service.record(db, actor=admin, action="SAFARI_CONFIGURATION_UPDATED", target_type="safari", target_id=item.id, reason=data.reason, previous_value=previous, new_value=audit_changes)
    db.commit(); item = db.scalar(_public_query().where(Safari.id == safari_id)); return _public_safari(db, item)


def list_notices(db: Session) -> list[SafariOperationalNoticeResponse]:
    return [SafariOperationalNoticeResponse.model_validate(value) for value in db.scalars(select(SafariOperationalNotice).order_by(SafariOperationalNotice.created_at.desc()))]


def create_notice(db: Session, admin: User, data: SafariOperationalNoticeCreate) -> SafariOperationalNoticeResponse:
    if data.safari_id is not None and db.get(Safari, data.safari_id) is None: raise HTTPException(status_code=404, detail="Safari not found")
    values = data.model_dump(exclude={"reason"}); item = SafariOperationalNotice(**values); db.add(item); db.flush()
    audit_service.record(db, actor=admin, action="SAFARI_NOTICE_CREATED", target_type="safari_operational_notice", target_id=item.id, reason=data.reason, new_value={"safari_id": item.safari_id, "title": item.title, "is_active": item.is_active})
    db.commit(); db.refresh(item); return SafariOperationalNoticeResponse.model_validate(item)


def update_notice(db: Session, admin: User, notice_id: int, data: SafariOperationalNoticeUpdate) -> SafariOperationalNoticeResponse:
    item = db.get(SafariOperationalNotice, notice_id)
    if item is None: raise HTTPException(status_code=404, detail="Safari notice not found")
    changes = data.model_dump(exclude={"reason"}, exclude_unset=True)
    audit_changes = data.model_dump(exclude={"reason"}, exclude_unset=True, mode="json")
    previous = {key: value.isoformat() if isinstance((value := getattr(item, key)), datetime) else value for key in changes}
    for key, value in changes.items(): setattr(item, key, value)
    if item.effective_from and item.effective_until and item.effective_until <= item.effective_from: raise HTTPException(status_code=422, detail="effective_until must be after effective_from")
    audit_service.record(db, actor=admin, action="SAFARI_NOTICE_UPDATED", target_type="safari_operational_notice", target_id=item.id, reason=data.reason, previous_value=previous, new_value=audit_changes)
    db.commit(); db.refresh(item); return SafariOperationalNoticeResponse.model_validate(item)

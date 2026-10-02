from __future__ import annotations

import hashlib
import ipaddress
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.advertising import AdvertiserProfile, AdvertiserStatus, AdvertiserType, AdvertisingCampaign, AdvertisingCampaignStatus, AdvertisingEvent, AdvertisingEventType, AdvertisingPlacement
from app.models.booking import Payment, PaymentPurpose, PaymentReconciliationStatus, PaymentStatus
from app.models.communication import NotificationEventType
from app.models.hotel import Hotel, HotelStatus
from app.models.hotel_verification import HotelVerification, VerificationStatus
from app.models.user import User
from app.repositories import destination_repository, hotel_repository
from app.schemas.advertising import AdvertiserProfileUpsert, AdvertisingPlan, CampaignCreate, CampaignResponse, ExternalCampaignCreate, ExternalCampaignUpdate, PublicCampaign
from app.services import audit_service, media_storage, notification_service, payment_provider


def configured_plans() -> list[AdvertisingPlan]:
    try:
        raw = json.loads(settings.ADVERTISING_PLANS_JSON)
        plans = [AdvertisingPlan.model_validate(item) for item in raw]
    except Exception as exc:
        raise RuntimeError("ADVERTISING_PLANS_JSON is invalid") from exc
    if not plans or len({item.code for item in plans}) != len(plans):
        raise RuntimeError("Advertising plan codes must be configured and unique")
    return plans


def _plan(code: str) -> AdvertisingPlan:
    match = next((item for item in configured_plans() if item.code == code), None)
    if match is None:
        raise HTTPException(status_code=422, detail="Unknown advertising plan")
    return match


def _owned_hotel(db: Session, user: User) -> Hotel:
    hotel = hotel_repository.get_hotel_by_partner_id(db, user.id)
    if hotel is None:
        raise HTTPException(status_code=404, detail="Hotel not found")
    return hotel


def _eligible(db: Session, hotel: Hotel) -> bool:
    approved = db.scalar(select(HotelVerification.id).where(HotelVerification.hotel_id == hotel.id, HotelVerification.verification_status == VerificationStatus.APPROVED))
    return hotel.status == HotelStatus.ACTIVE and approved is not None


def require_eligible(db: Session, hotel: Hotel) -> None:
    if not _eligible(db, hotel):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only an active, verified hotel can advertise")


def _payment(db: Session, campaign_id: int) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.advertising_campaign_id == campaign_id).order_by(Payment.id.desc()))


def _counts(db: Session, campaign_id: int) -> tuple[int, int]:
    row = db.execute(select(
        func.sum(case((AdvertisingEvent.event_type == AdvertisingEventType.IMPRESSION, 1), else_=0)),
        func.sum(case((AdvertisingEvent.event_type == AdvertisingEventType.CLICK, 1), else_=0)),
    ).where(AdvertisingEvent.campaign_id == campaign_id)).one()
    return int(row[0] or 0), int(row[1] or 0)


def normalize_external_url(value: str) -> str:
    """Return a conservative public HTTPS destination or reject it."""
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").rstrip(".").lower()
        if parsed.scheme.lower() != "https" or not host or parsed.username or parsed.password:
            raise ValueError
        if parsed.port not in (None, 443):
            raise ValueError
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")) or "." not in host:
            raise ValueError
        try:
            address = ipaddress.ip_address(host.strip("[]"))
            if not address.is_global:
                raise ValueError
        except ValueError as exc:
            # A ValueError from ip_address means this is a DNS name. A
            # ValueError raised for a parsed IP must remain rejected.
            if all(part.isdigit() for part in host.split(".")) or ":" in host:
                raise HTTPException(status_code=422, detail="Destination must not use a private or local address") from exc
        return urlunsplit(("https", parsed.netloc.lower(), parsed.path or "/", parsed.query, ""))
    except HTTPException:
        raise
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(status_code=422, detail="Destination must be a valid public HTTPS URL without credentials") from exc


def _profile(db: Session, user: User, *, required: bool = True) -> AdvertiserProfile | None:
    profile = db.scalar(select(AdvertiserProfile).where(AdvertiserProfile.user_id == user.id))
    if profile is None and required:
        raise HTTPException(status_code=404, detail="Advertiser profile not found")
    return profile


def upsert_profile(db: Session, user: User, data: AdvertiserProfileUpsert) -> AdvertiserProfile:
    website = normalize_external_url(data.website) if data.website else None
    profile = _profile(db, user, required=False)
    created = profile is None
    if profile is None:
        profile = AdvertiserProfile(user_id=user.id)
        db.add(profile)
    elif profile.status == AdvertiserStatus.SUSPENDED:
        raise HTTPException(status_code=409, detail="Suspended advertisers cannot update their profile")
    for key, value in data.model_dump().items():
        setattr(profile, key, website if key == "website" else value)
    db.flush()
    audit_service.record(db, actor=user, action="ADVERTISER_CREATED" if created else "ADVERTISER_UPDATED", target_type="advertiser_profile", target_id=profile.id, reason="Advertiser profile created" if created else "Advertiser profile updated", new_value={"business_name": profile.business_name, "status": profile.status.value})
    db.commit(); db.refresh(profile)
    return profile


def response(db: Session, item: AdvertisingCampaign) -> CampaignResponse:
    payment = _payment(db, item.id)
    impressions, clicks = _counts(db, item.id)
    return CampaignResponse(
        id=item.id, public_id=item.public_id, advertiser_type=item.advertiser_type,
        advertiser_profile_id=item.advertiser_profile_id,
        advertiser_name=item.hotel.name if item.hotel else (item.advertiser_profile.business_name if item.advertiser_profile else None),
        advertiser_status=item.advertiser_profile.status if item.advertiser_profile else None,
        hotel_id=item.hotel_id, campaign_name=item.campaign_name, headline=item.headline,
        short_copy=item.short_copy, target_url=item.target_url,
        hotel_name=item.hotel.name if item.hotel else None, placement=item.placement,
        plan_code=item.plan_code, district_id=item.district_id, destination_id=item.destination_id,
        district_name=item.district.name if item.district else None,
        destination_name=item.destination.name if item.destination else None,
        creative_url=item.creative_url, alt_text=item.alt_text, status=item.status,
        start_at=item.start_at, end_at=item.end_at, price_amount=item.price_amount,
        currency=item.currency, payment_status=payment.status if payment else PaymentStatus.NOT_STARTED,
        payment_reference=payment.provider_payment_id if payment else None,
        review_reason=item.review_reason, refund_review_required=item.refund_review_required,
        creative_rights_confirmed=item.creative_rights_confirmed, creative_source=item.creative_source,
        version=item.version, impressions=impressions, clicks=clicks,
        submitted_at=item.submitted_at, reviewed_at=item.reviewed_at, created_at=item.created_at,
    )


def _query():
    return select(AdvertisingCampaign).options(
        selectinload(AdvertisingCampaign.hotel), selectinload(AdvertisingCampaign.advertiser_profile), selectinload(AdvertisingCampaign.district), selectinload(AdvertisingCampaign.destination)
    )


def create(db: Session, user: User, data: CampaignCreate) -> CampaignResponse:
    hotel = _owned_hotel(db, user)
    require_eligible(db, hotel)
    plan = _plan(data.plan_code)
    start_at = data.start_at if data.start_at.tzinfo else data.start_at.replace(tzinfo=timezone.utc)
    if start_at < datetime.now(timezone.utc) - timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Campaign start cannot be in the past")
    district = destination = None
    if plan.placement == AdvertisingPlacement.DESTINATION_PROMOTION:
        if not data.district_slug:
            raise HTTPException(status_code=422, detail="A district is required for this placement")
        district = destination_repository.get_district_by_slug(db, data.district_slug)
        if district is None:
            raise HTTPException(status_code=422, detail="Unknown district")
        if data.destination_slug:
            destination = destination_repository.get_destination_by_identity(db, district.id, data.destination_slug)
            if destination is None:
                raise HTTPException(status_code=422, detail="Unknown destination")
    item = AdvertisingCampaign(
        advertiser_type=AdvertiserType.HOTEL, hotel_id=hotel.id, placement=plan.placement, plan_code=plan.code,
        district_id=district.id if district else None, destination_id=destination.id if destination else None,
        start_at=start_at, end_at=start_at + timedelta(days=plan.duration_days),
        price_amount=plan.amount, currency=plan.currency.upper(), alt_text=data.alt_text,
    )
    db.add(item); db.flush()
    audit_service.record(db, actor=user, action="CAMPAIGN_CREATED", target_type="advertising_campaign", target_id=item.id, reason="Hotel campaign draft created", new_value={"advertiser_type": "HOTEL", "status": item.status.value})
    db.commit()
    item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def create_external(db: Session, user: User, data: ExternalCampaignCreate) -> CampaignResponse:
    profile = _profile(db, user)
    if profile.status != AdvertiserStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Suspended advertisers cannot create campaigns")
    if not data.creative_rights_confirmed:
        raise HTTPException(status_code=422, detail="Creative rights authorization must be confirmed")
    plan = _plan(data.plan_code)
    start_at = data.start_at if data.start_at.tzinfo else data.start_at.replace(tzinfo=timezone.utc)
    if start_at < datetime.now(timezone.utc) - timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Campaign start cannot be in the past")
    district = destination = None
    if plan.placement == AdvertisingPlacement.DESTINATION_PROMOTION:
        if not data.district_slug:
            raise HTTPException(status_code=422, detail="A district is required for this placement")
        district = destination_repository.get_district_by_slug(db, data.district_slug)
        if district is None:
            raise HTTPException(status_code=422, detail="Unknown district")
        if data.destination_slug:
            destination = destination_repository.get_destination_by_identity(db, district.id, data.destination_slug)
            if destination is None:
                raise HTTPException(status_code=422, detail="Unknown destination")
    item = AdvertisingCampaign(
        advertiser_type=AdvertiserType.EXTERNAL, advertiser_profile_id=profile.id,
        campaign_name=" ".join(data.campaign_name.split()), headline=" ".join(data.headline.split()),
        short_copy=" ".join(data.short_copy.split()), target_url=normalize_external_url(data.target_url),
        placement=plan.placement, plan_code=plan.code, district_id=district.id if district else None,
        destination_id=destination.id if destination else None, start_at=start_at,
        end_at=start_at + timedelta(days=plan.duration_days), price_amount=plan.amount,
        currency=plan.currency.upper(), alt_text=data.alt_text,
        creative_rights_confirmed=True, creative_source=(data.creative_source or "").strip() or None,
    )
    db.add(item); db.flush()
    audit_service.record(db, actor=user, action="CAMPAIGN_CREATED", target_type="advertising_campaign", target_id=item.id, reason="External campaign draft created", new_value={"advertiser_type": "EXTERNAL", "status": item.status.value})
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def list_external(db: Session, user: User) -> list[CampaignResponse]:
    profile = _profile(db, user)
    refresh_due(db)
    return [response(db, item) for item in db.scalars(_query().where(AdvertisingCampaign.advertiser_profile_id == profile.id).order_by(AdvertisingCampaign.created_at.desc()))]


def _owned_external_campaign(db: Session, user: User, campaign_id: int, *, lock: bool = False) -> AdvertisingCampaign:
    profile = _profile(db, user)
    query = _query().where(AdvertisingCampaign.id == campaign_id, AdvertisingCampaign.advertiser_profile_id == profile.id, AdvertisingCampaign.advertiser_type == AdvertiserType.EXTERNAL)
    if lock: query = query.with_for_update()
    item = db.scalar(query)
    if item is None: raise HTTPException(status_code=404, detail="Campaign not found")
    return item


def update_external(db: Session, user: User, campaign_id: int, data: ExternalCampaignUpdate) -> CampaignResponse:
    item = _owned_external_campaign(db, user, campaign_id, lock=True)
    if item.advertiser_profile.status != AdvertiserStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Suspended advertisers cannot edit campaigns")
    if item.version != data.version:
        raise HTTPException(status_code=409, detail="Campaign was updated elsewhere; reload before saving")
    if item.status in (AdvertisingCampaignStatus.EXPIRED, AdvertisingCampaignStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Campaign cannot be edited in its current state")
    changes = data.model_dump(exclude_unset=True); changes.pop("version", None)
    if changes.get("target_url") is not None: changes["target_url"] = normalize_external_url(changes["target_url"])
    if changes.get("creative_rights_confirmed") is False:
        raise HTTPException(status_code=422, detail="Creative rights authorization must remain confirmed")
    material = any(key in changes and getattr(item, key) != value for key, value in changes.items() if key in {"headline", "short_copy", "target_url"})
    previous = item.status
    for key, value in changes.items(): setattr(item, key, value.strip() if isinstance(value, str) else value)
    if material and item.status in (AdvertisingCampaignStatus.PENDING_REVIEW, AdvertisingCampaignStatus.SCHEDULED, AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.REJECTED):
        item.status = AdvertisingCampaignStatus.NEEDS_CHANGES
        item.approved_at = None; item.approved_target_url = None
    item.version += 1
    audit_service.record(db, actor=user, action="TARGET_CHANGED" if "target_url" in changes else "CAMPAIGN_UPDATED", target_type="advertising_campaign", target_id=item.id, reason="Advertiser updated campaign content", previous_value={"status": previous.value}, new_value={"status": item.status.value, "version": item.version})
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def list_partner(db: Session, user: User) -> list[CampaignResponse]:
    hotel = _owned_hotel(db, user)
    refresh_due(db)
    return [response(db, item) for item in db.scalars(_query().where(AdvertisingCampaign.hotel_id == hotel.id).order_by(AdvertisingCampaign.created_at.desc()))]


def _owned_campaign(db: Session, user: User, campaign_id: int, *, lock: bool = False) -> AdvertisingCampaign:
    hotel = _owned_hotel(db, user)
    query = _query().where(AdvertisingCampaign.id == campaign_id, AdvertisingCampaign.hotel_id == hotel.id)
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return item


async def upload_creative(db: Session, user: User, campaign_id: int, file: UploadFile, alt_text: str | None) -> CampaignResponse:
    item = _owned_campaign(db, user, campaign_id)
    if item.status not in (AdvertisingCampaignStatus.DRAFT, AdvertisingCampaignStatus.PAYMENT_PENDING, AdvertisingCampaignStatus.NEEDS_CHANGES):
        raise HTTPException(status_code=409, detail="Creative cannot be changed in the current campaign state")
    old_key = item.creative_storage_key
    url, key, content_type, size = await media_storage.store_campaign_creative(item.hotel_id, item.id, file)
    item.creative_url, item.creative_storage_key = url, key
    item.creative_content_type, item.creative_size = content_type, size
    item.alt_text = (alt_text or item.alt_text or item.hotel.name).strip()[:255]
    db.commit(); media_storage.delete_stored_file(old_key)
    item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


async def upload_external_creative(db: Session, user: User, campaign_id: int, file: UploadFile, alt_text: str | None, rights_confirmed: bool, source: str | None) -> CampaignResponse:
    item = _owned_external_campaign(db, user, campaign_id, lock=True)
    if item.advertiser_profile.status != AdvertiserStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Suspended advertisers cannot change creatives")
    if not rights_confirmed:
        raise HTTPException(status_code=422, detail="Creative rights authorization must be confirmed")
    if item.status in (AdvertisingCampaignStatus.EXPIRED, AdvertisingCampaignStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Creative cannot be changed in the current campaign state")
    previous = item.status; old_key = item.creative_storage_key
    url, key, content_type, size, width, height = await media_storage.store_external_campaign_creative(item.advertiser_profile_id, item.id, file)
    item.creative_url, item.creative_storage_key = url, key
    item.creative_content_type, item.creative_size = content_type, size
    item.creative_width, item.creative_height = width, height
    item.alt_text = (alt_text or item.alt_text or item.headline or item.advertiser_profile.business_name).strip()[:255]
    item.creative_rights_confirmed = True; item.creative_source = (source or "").strip()[:255] or None
    if item.status in (AdvertisingCampaignStatus.PENDING_REVIEW, AdvertisingCampaignStatus.SCHEDULED, AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.REJECTED):
        item.status = AdvertisingCampaignStatus.NEEDS_CHANGES; item.approved_at = None; item.approved_target_url = None
    item.version += 1
    audit_service.record(db, actor=user, action="CREATIVE_REPLACED" if old_key else "CREATIVE_UPLOADED", target_type="advertising_campaign", target_id=item.id, reason="Advertiser supplied authorized campaign creative", previous_value={"status": previous.value}, new_value={"status": item.status.value, "version": item.version})
    db.commit(); media_storage.delete_stored_file(old_key)
    item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def create_payment_order(db: Session, user: User, campaign_id: int) -> Payment:
    if settings.PAYMENT_MODE == "disabled":
        raise HTTPException(status_code=503, detail="Payment processing is disabled")
    item = _owned_campaign(db, user, campaign_id, lock=True)
    require_eligible(db, item.hotel)
    existing = _payment(db, item.id)
    if existing and existing.status in (PaymentStatus.PENDING, PaymentStatus.PAID):
        return existing
    provider = payment_provider.configured_provider()
    order = provider.create_order(amount=item.price_amount, currency=item.currency, booking_reference=f"AD-{item.public_id}")
    payment = Payment(booking_id=None, verification_hotel_id=None, advertising_campaign_id=item.id,
        purpose=PaymentPurpose.ADVERTISING_CAMPAIGN, provider=provider.name,
        provider_order_id=order.provider_order_id, amount=item.price_amount,
        currency=item.currency, status=PaymentStatus.PENDING)
    item.status = AdvertisingCampaignStatus.PAYMENT_PENDING
    db.add(payment); db.commit(); db.refresh(payment)
    return payment


def create_external_payment_order(db: Session, user: User, campaign_id: int) -> Payment:
    if settings.PAYMENT_MODE == "disabled": raise HTTPException(status_code=503, detail="Payment processing is disabled")
    item = _owned_external_campaign(db, user, campaign_id, lock=True)
    if item.advertiser_profile.status != AdvertiserStatus.ACTIVE:
        raise HTTPException(status_code=409, detail="Suspended advertisers cannot pay for campaigns")
    existing = _payment(db, item.id)
    if existing and existing.status in (PaymentStatus.PENDING, PaymentStatus.PAID): return existing
    provider = payment_provider.configured_provider()
    order = provider.create_order(amount=item.price_amount, currency=item.currency, booking_reference=f"AD-{item.public_id}")
    payment = Payment(booking_id=None, verification_hotel_id=None, advertising_campaign_id=item.id, purpose=PaymentPurpose.ADVERTISING_CAMPAIGN, provider=provider.name, provider_order_id=order.provider_order_id, amount=item.price_amount, currency=item.currency, status=PaymentStatus.PENDING)
    item.status = AdvertisingCampaignStatus.PAYMENT_PENDING
    db.add(payment); db.commit(); db.refresh(payment)
    return payment


def submit(db: Session, user: User, campaign_id: int) -> CampaignResponse:
    item = _owned_campaign(db, user, campaign_id, lock=True)
    require_eligible(db, item.hotel)
    payment = _payment(db, item.id)
    if payment is None or payment.status != PaymentStatus.PAID:
        raise HTTPException(status_code=409, detail="A successful campaign payment is required before review")
    if not item.creative_url:
        raise HTTPException(status_code=409, detail="Upload campaign creative before review")
    if item.status not in (AdvertisingCampaignStatus.PAYMENT_PENDING, AdvertisingCampaignStatus.NEEDS_CHANGES, AdvertisingCampaignStatus.DRAFT):
        raise HTTPException(status_code=409, detail="Campaign is not ready for submission")
    item.status = AdvertisingCampaignStatus.PENDING_REVIEW
    item.submitted_at = datetime.now(timezone.utc)
    item.review_reason = None
    audit_service.record(db, actor=user, action="CAMPAIGN_SUBMITTED", target_type="advertising_campaign", target_id=item.id, reason="Paid Hotel campaign submitted for Maharashtra Tourist Places review", new_value={"status": item.status.value})
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def submit_external(db: Session, user: User, campaign_id: int) -> CampaignResponse:
    item = _owned_external_campaign(db, user, campaign_id, lock=True)
    if item.advertiser_profile.status != AdvertiserStatus.ACTIVE: raise HTTPException(status_code=409, detail="Suspended advertisers cannot submit campaigns")
    payment = _payment(db, item.id)
    if payment is None or payment.status != PaymentStatus.PAID: raise HTTPException(status_code=409, detail="A successful campaign payment is required before review")
    if not item.creative_url or not item.creative_rights_confirmed or not item.target_url: raise HTTPException(status_code=409, detail="A valid creative, rights confirmation, and destination are required before review")
    if item.status not in (AdvertisingCampaignStatus.PAYMENT_PENDING, AdvertisingCampaignStatus.NEEDS_CHANGES, AdvertisingCampaignStatus.DRAFT, AdvertisingCampaignStatus.REJECTED): raise HTTPException(status_code=409, detail="Campaign is not ready for submission")
    item.status = AdvertisingCampaignStatus.PENDING_REVIEW; item.submitted_at = datetime.now(timezone.utc); item.review_reason = None; item.version += 1
    audit_service.record(db, actor=user, action="CAMPAIGN_SUBMITTED", target_type="advertising_campaign", target_id=item.id, reason="Paid campaign submitted for Maharashtra Tourist Places review", new_value={"status": item.status.value})
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id)); return response(db, item)


def cancel(db: Session, user: User, campaign_id: int) -> CampaignResponse:
    item = _owned_campaign(db, user, campaign_id, lock=True)
    if item.status in (AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.EXPIRED, AdvertisingCampaignStatus.REJECTED, AdvertisingCampaignStatus.CANCELLED):
        raise HTTPException(status_code=409, detail="Campaign cannot be cancelled in its current state")
    item.status = AdvertisingCampaignStatus.CANCELLED
    audit_service.record(db, actor=user, action="CAMPAIGN_CANCELLED", target_type="advertising_campaign", target_id=item.id, reason="Hotel Partner cancelled campaign", new_value={"status": item.status.value})
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def cancel_external(db: Session, user: User, campaign_id: int) -> CampaignResponse:
    item = _owned_external_campaign(db, user, campaign_id, lock=True)
    if item.status in (AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.EXPIRED, AdvertisingCampaignStatus.REJECTED, AdvertisingCampaignStatus.CANCELLED): raise HTTPException(status_code=409, detail="Campaign cannot be cancelled in its current state")
    item.status = AdvertisingCampaignStatus.CANCELLED; item.version += 1
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id)); return response(db, item)


def list_admin(db: Session, status_filter: AdvertisingCampaignStatus | None, advertiser_type: AdvertiserType | None = None, payment_status: PaymentStatus | None = None, placement: AdvertisingPlacement | None = None, query_text: str | None = None) -> list[CampaignResponse]:
    refresh_due(db)
    query = _query()
    if status_filter: query = query.where(AdvertisingCampaign.status == status_filter)
    if advertiser_type: query = query.where(AdvertisingCampaign.advertiser_type == advertiser_type)
    if placement: query = query.where(AdvertisingCampaign.placement == placement)
    if payment_status: query = query.join(Payment, Payment.advertising_campaign_id == AdvertisingCampaign.id).where(Payment.status == payment_status)
    if query_text:
        pattern = f"%{query_text.strip()}%"
        query = query.outerjoin(Hotel, Hotel.id == AdvertisingCampaign.hotel_id).outerjoin(AdvertiserProfile, AdvertiserProfile.id == AdvertisingCampaign.advertiser_profile_id).where(or_(Hotel.name.ilike(pattern), AdvertiserProfile.business_name.ilike(pattern), AdvertisingCampaign.campaign_name.ilike(pattern)))
    return [response(db, item) for item in db.scalars(query.order_by(AdvertisingCampaign.created_at.desc()))]


def suspend_advertiser(db: Session, admin: User, profile_id: int, suspended: bool, reason: str) -> AdvertiserProfile:
    profile = db.scalar(select(AdvertiserProfile).where(AdvertiserProfile.id == profile_id).with_for_update())
    if profile is None: raise HTTPException(status_code=404, detail="Advertiser not found")
    normalized = reason.strip()
    if len(normalized) < 2: raise HTTPException(status_code=422, detail="A reason is required")
    now = datetime.now(timezone.utc)
    profile.status = AdvertiserStatus.SUSPENDED if suspended else AdvertiserStatus.ACTIVE
    profile.suspended_reason = normalized if suspended else None; profile.suspended_at = now if suspended else None; profile.suspended_by = admin.id if suspended else None
    if suspended:
        for campaign in db.scalars(select(AdvertisingCampaign).where(AdvertisingCampaign.advertiser_profile_id == profile.id, AdvertisingCampaign.status.in_((AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.SCHEDULED)))):
            campaign.status = AdvertisingCampaignStatus.PAUSED; campaign.paused_at = now; campaign.review_reason = normalized
    audit_service.record(db, actor=admin, action="ADVERTISER_SUSPENDED" if suspended else "ADVERTISER_REACTIVATED", target_type="advertiser_profile", target_id=profile.id, reason=normalized, new_value={"status": profile.status.value})
    db.commit(); db.refresh(profile); return profile


def review(db: Session, admin: User, campaign_id: int, action: str, reason: str | None) -> CampaignResponse:
    item = db.scalar(_query().where(AdvertisingCampaign.id == campaign_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    normalized_reason = (reason or "").strip()
    if action in ("REQUEST_CHANGES", "REJECT", "PAUSE") and len(normalized_reason) < 2:
        raise HTTPException(status_code=422, detail="A reason is required for this action")
    payment = _payment(db, item.id)
    previous = item.status
    now = datetime.now(timezone.utc)
    if action == "APPROVE":
        if item.status in (AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.SCHEDULED) and item.approved_at:
            return response(db, item)
        if item.status != AdvertisingCampaignStatus.PENDING_REVIEW or payment is None or payment.status != PaymentStatus.PAID:
            raise HTTPException(status_code=409, detail="Only a paid campaign pending review can be approved")
        if _aware(item.end_at) <= now:
            raise HTTPException(status_code=409, detail="Campaign schedule has elapsed; request updated dates")
        if item.advertiser_type == AdvertiserType.HOTEL:
            require_eligible(db, item.hotel)
        elif not item.advertiser_profile or item.advertiser_profile.status != AdvertiserStatus.ACTIVE:
            raise HTTPException(status_code=409, detail="Advertiser is not active")
        if item.advertiser_type == AdvertiserType.EXTERNAL:
            item.target_url = normalize_external_url(item.target_url or "")
            item.approved_target_url = item.target_url
        item.status = AdvertisingCampaignStatus.ACTIVE if _aware(item.start_at) <= now < _aware(item.end_at) else AdvertisingCampaignStatus.SCHEDULED
        item.approved_at = now
        event_type, title = NotificationEventType.ADVERTISING_APPROVED, "Advertising campaign approved"
    elif action == "REQUEST_CHANGES":
        if item.status == AdvertisingCampaignStatus.NEEDS_CHANGES:
            return response(db, item)
        if item.status != AdvertisingCampaignStatus.PENDING_REVIEW:
            raise HTTPException(status_code=409, detail="Campaign is not pending review")
        item.status = AdvertisingCampaignStatus.NEEDS_CHANGES
        event_type, title = NotificationEventType.ADVERTISING_CHANGES_REQUESTED, "Campaign changes requested"
    elif action == "REJECT":
        if item.status == AdvertisingCampaignStatus.REJECTED:
            return response(db, item)
        if item.status != AdvertisingCampaignStatus.PENDING_REVIEW:
            raise HTTPException(status_code=409, detail="Campaign is not pending review")
        item.status = AdvertisingCampaignStatus.REJECTED
        item.refund_review_required = bool(payment and payment.status == PaymentStatus.PAID)
        event_type, title = NotificationEventType.ADVERTISING_REJECTED, "Advertising campaign rejected"
    elif action == "PAUSE":
        if item.status == AdvertisingCampaignStatus.PAUSED:
            return response(db, item)
        if item.status not in (AdvertisingCampaignStatus.ACTIVE, AdvertisingCampaignStatus.SCHEDULED):
            raise HTTPException(status_code=409, detail="Only an active or scheduled campaign can be paused")
        item.status, item.paused_at = AdvertisingCampaignStatus.PAUSED, now
        event_type, title = NotificationEventType.ADVERTISING_PAUSED, "Advertising campaign paused"
    else:
        raise HTTPException(status_code=422, detail="Unknown review action")
    item.review_reason = normalized_reason or None
    item.reviewed_by, item.reviewed_at = admin.id, now
    audit_service.record(db, actor=admin, action=f"ADVERTISING_{action}", target_type="advertising_campaign", target_id=item.id,
        reason=normalized_reason or "Campaign approved after review", previous_value={"status": previous.value}, new_value={"status": item.status.value})
    recipient_id = item.hotel.partner_id if item.hotel and item.hotel.partner_id else (item.advertiser_profile.user_id if item.advertiser_profile else None)
    if recipient_id:
        notification_service.create(db, recipient_user_id=recipient_id, event_type=event_type,
            dedupe_key=f"advertising:{item.id}:{item.status.value}:{item.reviewed_at.isoformat()}", title=title,
            body=normalized_reason or "Your advertising campaign was approved.", data={"campaign_id": item.id, "hotel_id": item.hotel_id})
    db.commit(); item = db.scalar(_query().where(AdvertisingCampaign.id == item.id))
    return response(db, item)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def refresh_due(db: Session, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    items = list(db.scalars(select(AdvertisingCampaign).where(AdvertisingCampaign.status.in_((AdvertisingCampaignStatus.SCHEDULED, AdvertisingCampaignStatus.ACTIVE)))))
    changed = 0
    for item in items:
        previous = item.status
        if _aware(item.end_at) <= current:
            item.status = AdvertisingCampaignStatus.EXPIRED; changed += 1
        elif item.status == AdvertisingCampaignStatus.SCHEDULED and _aware(item.start_at) <= current:
            item.status = AdvertisingCampaignStatus.ACTIVE; changed += 1
        if item.status != previous and item.reviewed_by:
            actor = db.get(User, item.reviewed_by)
            if actor:
                audit_service.record(db, actor=actor, action="CAMPAIGN_EXPIRED" if item.status == AdvertisingCampaignStatus.EXPIRED else "CAMPAIGN_ACTIVATED", target_type="advertising_campaign", target_id=item.id, reason="Campaign lifecycle advanced automatically from its authorized schedule", previous_value={"status": previous.value}, new_value={"status": item.status.value})
    if changed: db.commit()
    return changed


def public_campaigns(db: Session, placement: AdvertisingPlacement, district_slug: str | None, destination_slug: str | None) -> list[PublicCampaign]:
    refresh_due(db)
    now = datetime.now(timezone.utc)
    query = _query().outerjoin(Hotel, Hotel.id == AdvertisingCampaign.hotel_id).outerjoin(HotelVerification, HotelVerification.hotel_id == AdvertisingCampaign.hotel_id).outerjoin(AdvertiserProfile, AdvertiserProfile.id == AdvertisingCampaign.advertiser_profile_id).where(
        AdvertisingCampaign.placement == placement, AdvertisingCampaign.status == AdvertisingCampaignStatus.ACTIVE,
        AdvertisingCampaign.start_at <= now, AdvertisingCampaign.end_at > now,
        AdvertisingCampaign.creative_url.is_not(None),
        or_(
            (AdvertisingCampaign.advertiser_type == AdvertiserType.HOTEL) & (Hotel.status == HotelStatus.ACTIVE) & (HotelVerification.verification_status == VerificationStatus.APPROVED),
            (AdvertisingCampaign.advertiser_type == AdvertiserType.EXTERNAL) & (AdvertiserProfile.status == AdvertiserStatus.ACTIVE) & (AdvertisingCampaign.approved_target_url.is_not(None)),
        ),
    ).join(Payment, Payment.advertising_campaign_id == AdvertisingCampaign.id).where(Payment.status == PaymentStatus.PAID, Payment.purpose == PaymentPurpose.ADVERTISING_CAMPAIGN)
    if placement == AdvertisingPlacement.DESTINATION_PROMOTION:
        district = destination_repository.get_district_by_slug(db, district_slug or "")
        target_destination = None
        if district is None: return []
        query = query.where(AdvertisingCampaign.district_id == district.id)
        if destination_slug:
            target_destination = destination_repository.get_destination_by_identity(db, district.id, destination_slug)
            if target_destination is None: return []
        if target_destination:
            query = query.where(or_(AdvertisingCampaign.destination_id.is_(None), AdvertisingCampaign.destination_id == target_destination.id))
    return [PublicCampaign(id=item.public_id, placement=item.placement, creative_url=item.creative_url or "",
        alt_text=item.alt_text or (item.hotel.name if item.hotel else item.advertiser_profile.business_name),
        advertiser_name=item.hotel.name if item.hotel else item.advertiser_profile.business_name,
        headline=item.headline, short_copy=item.short_copy, advertiser_type=item.advertiser_type,
        is_external=item.advertiser_type == AdvertiserType.EXTERNAL,
        destination_url=(f"/hotels/{item.hotel.slug}" if item.advertiser_type == AdvertiserType.HOTEL else f"{settings.MEDIA_BASE_URL.rstrip('/')}/api/v1/ads/{item.public_id}/click"))
        for item in db.scalars(query.order_by(AdvertisingCampaign.approved_at, AdvertisingCampaign.id))]


def record_event(db: Session, public_id: str, event_type: AdvertisingEventType, event_id: str, fingerprint: str) -> bool:
    refresh_due(db)
    now = datetime.now(timezone.utc)
    item = db.scalar(_query().outerjoin(Hotel, Hotel.id == AdvertisingCampaign.hotel_id).outerjoin(HotelVerification, HotelVerification.hotel_id == AdvertisingCampaign.hotel_id).outerjoin(AdvertiserProfile, AdvertiserProfile.id == AdvertisingCampaign.advertiser_profile_id)
        .join(Payment, Payment.advertising_campaign_id == AdvertisingCampaign.id)
        .where(AdvertisingCampaign.public_id == public_id, AdvertisingCampaign.status == AdvertisingCampaignStatus.ACTIVE,
            AdvertisingCampaign.start_at <= now, AdvertisingCampaign.end_at > now,
            or_(
                (AdvertisingCampaign.advertiser_type == AdvertiserType.HOTEL) & (Hotel.status == HotelStatus.ACTIVE) & (HotelVerification.verification_status == VerificationStatus.APPROVED),
                (AdvertisingCampaign.advertiser_type == AdvertiserType.EXTERNAL) & (AdvertiserProfile.status == AdvertiserStatus.ACTIVE) & (AdvertisingCampaign.approved_target_url.is_not(None)),
            ),
            Payment.status == PaymentStatus.PAID, Payment.purpose == PaymentPurpose.ADVERTISING_CAMPAIGN))
    if item is None:
        raise HTTPException(status_code=404, detail="Active campaign not found")
    now = datetime.now(timezone.utc)
    seconds = settings.ADVERTISING_EVENT_DEDUPE_SECONDS
    bucket = datetime.fromtimestamp((int(now.timestamp()) // seconds) * seconds, tz=timezone.utc)
    # One event of each kind per visitor fingerprint and time bucket. The
    # client event id is accepted for retry semantics but cannot be rotated to
    # inflate metrics within the configured anti-spam window.
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{item.id}:{fingerprint}".encode()).hexdigest()
    db.add(AdvertisingEvent(campaign_id=item.id, event_type=event_type, dedupe_hash=digest, bucket_start=bucket))
    try:
        db.commit(); return True
    except IntegrityError:
        db.rollback(); return False


def click_destination(db: Session, public_id: str, fingerprint: str) -> str:
    item = db.scalar(_query().where(AdvertisingCampaign.public_id == public_id))
    if item is None: raise HTTPException(status_code=404, detail="Active campaign not found")
    record_event(db, public_id, AdvertisingEventType.CLICK, f"redirect-{public_id}", fingerprint)
    if item.advertiser_type == AdvertiserType.HOTEL and item.hotel:
        return f"{settings.APP_BASE_URL.rstrip('/')}/hotels/{item.hotel.slug}"
    if item.advertiser_type == AdvertiserType.EXTERNAL and item.approved_target_url:
        return normalize_external_url(item.approved_target_url)
    raise HTTPException(status_code=404, detail="Approved campaign destination not found")


def payment_succeeded(db: Session, payment: Payment) -> None:
    item = db.get(AdvertisingCampaign, payment.advertising_campaign_id) if payment.advertising_campaign_id else None
    if item:
        payment.reconciliation_status = PaymentReconciliationStatus.RESOLVED
        payment.reconciliation_resolved_at = datetime.now(timezone.utc)
        recipient_id = item.hotel.partner_id if item.hotel and item.hotel.partner_id else (item.advertiser_profile.user_id if item.advertiser_profile else None)
        if recipient_id:
            actor = db.get(User, recipient_id)
            if actor:
                audit_service.record(db, actor=actor, action="CAMPAIGN_PAID", target_type="advertising_campaign", target_id=item.id, reason="Provider-verified advertising payment received", new_value={"payment_id": payment.id, "status": payment.status.value})
            notification_service.create(db, recipient_user_id=recipient_id,
                event_type=NotificationEventType.ADVERTISING_PAYMENT_SUCCESS,
                dedupe_key=f"advertising-payment:{payment.id}:paid", title="Advertising payment successful",
                body="Your campaign payment was received. Submit the campaign for Admin review; payment does not guarantee approval.",
                data={"campaign_id": item.id, "hotel_id": item.hotel_id, "payment_id": payment.id})

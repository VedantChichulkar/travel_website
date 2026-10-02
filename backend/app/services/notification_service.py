"""Transactional in-app notifications and durable external delivery jobs."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.booking import Booking
from app.models.communication import Notification, NotificationChannel, NotificationEventType, NotificationJob, NotificationJobStatus
from app.models.hotel import Hotel
from app.models.user import User
from app.services import notification_provider


logger = logging.getLogger(__name__)


def _job_key(recipient_user_id: int, dedupe_key: str, channel: NotificationChannel) -> str:
    digest = hashlib.sha256(f"{recipient_user_id}:{dedupe_key}:{channel.value}".encode("utf-8")).hexdigest()
    return f"notification-{digest}"


def create(
    db: Session,
    *,
    recipient_user_id: int,
    event_type: NotificationEventType,
    dedupe_key: str,
    title: str,
    body: str,
    data: dict[str, object] | None = None,
    channels: tuple[NotificationChannel, ...] | None = None,
    external_body: str | None = None,
    delivery_expires_at: datetime | None = None,
    commit: bool = False,
) -> Notification:
    """Persist the independent in-app record and idempotent external jobs."""
    key = dedupe_key[:180]
    existing = db.scalar(select(Notification).where(Notification.recipient_user_id == recipient_user_id, Notification.dedupe_key == key).options(selectinload(Notification.jobs)))
    if existing:
        return existing
    notification = Notification(
        recipient_user_id=recipient_user_id, event_type=event_type, dedupe_key=key,
        title=title[:180], body=body, data=data or {},
    )
    recipient = db.get(User, recipient_user_id)
    for channel in tuple(NotificationChannel) if channels is None else channels:
        provider_name = notification_provider.configured_name(channel)
        address_available = bool(recipient and _recipient(recipient, channel))
        ready = bool(provider_name and address_available)
        notification.jobs.append(NotificationJob(
            channel=channel,
            status=NotificationJobStatus.PENDING if ready else NotificationJobStatus.PROVIDER_UNAVAILABLE,
            provider=provider_name,
            delivery_body=external_body,
            delivery_expires_at=delivery_expires_at,
            idempotency_key=_job_key(recipient_user_id, key, channel),
            next_retry_at=datetime.now(timezone.utc) if ready else None,
            last_error=None if ready else (
                "Recipient address is unavailable for this channel" if provider_name
                else "No transactional provider is configured for this channel"
            ),
        ))
    savepoint = db.begin_nested()
    db.add(notification)
    try:
        db.flush()
    except IntegrityError:
        savepoint.rollback()
        existing = db.scalar(select(Notification).where(Notification.recipient_user_id == recipient_user_id, Notification.dedupe_key == key).options(selectinload(Notification.jobs)))
        if existing:
            return existing
        raise
    else:
        savepoint.commit()
    if commit:
        db.commit(); db.refresh(notification)
    return notification


def for_booking(
    db: Session,
    booking: Booking,
    *,
    event_type: NotificationEventType,
    event_key: str,
    title: str,
    body: str,
    include_hotel: bool = True,
) -> list[Notification]:
    recipients = [booking.user_id]
    hotel = db.get(Hotel, booking.hotel_id)
    if include_hotel and hotel and hotel.partner_id:
        recipients.append(hotel.partner_id)
    return [create(
        db, recipient_user_id=recipient_id, event_type=event_type,
        dedupe_key=f"{event_type.value}:{event_key}", title=title, body=body,
        data={"booking_id": booking.id, "booking_reference": booking.booking_reference, "hotel_id": booking.hotel_id},
    ) for recipient_id in recipients]


def list_for_user(db: Session, user: User, *, limit: int = 100) -> tuple[list[Notification], int]:
    items = list(db.scalars(select(Notification).where(Notification.recipient_user_id == user.id).options(selectinload(Notification.jobs)).order_by(Notification.created_at.desc()).limit(limit)))
    unread = db.scalar(select(func.count(Notification.id)).where(Notification.recipient_user_id == user.id, Notification.read_at.is_(None))) or 0
    return items, int(unread)


def mark_read(db: Session, user: User, notification_id: int) -> Notification | None:
    item = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.recipient_user_id == user.id).options(selectinload(Notification.jobs)))
    if item is None:
        return None
    if item.read_at is None:
        item.read_at = datetime.now(timezone.utc)
        db.commit(); db.refresh(item)
    return item


def mark_all_read(db: Session, user: User) -> int:
    items = list(db.scalars(select(Notification).where(Notification.recipient_user_id == user.id, Notification.read_at.is_(None))))
    now = datetime.now(timezone.utc)
    for item in items:
        item.read_at = now
    db.commit()
    return len(items)


def _recipient(user: User, channel: NotificationChannel) -> str | None:
    return user.email if channel == NotificationChannel.EMAIL else user.phone


def _activate_newly_configured(db: Session, now: datetime, limit: int) -> int:
    jobs = list(db.scalars(
        select(NotificationJob)
        .where(NotificationJob.status == NotificationJobStatus.PROVIDER_UNAVAILABLE)
        .order_by(NotificationJob.id).limit(limit).with_for_update(skip_locked=True)
    ))
    changed = 0
    for job in jobs:
        provider_name = notification_provider.configured_name(job.channel)
        user = db.get(User, job.notification.recipient_user_id)
        if provider_name and user and _recipient(user, job.channel):
            job.provider = provider_name
            job.status = NotificationJobStatus.PENDING
            job.next_retry_at = now
            job.last_error = None
            changed += 1
        elif provider_name:
            job.provider = provider_name
            job.last_error = "Recipient address is unavailable for this channel"
    if changed:
        db.commit()
    return changed


def deliver_job(db: Session, job_id: int, *, now: datetime | None = None) -> NotificationJob:
    current = now or datetime.now(timezone.utc)
    job = db.scalar(
        select(NotificationJob).where(NotificationJob.id == job_id)
        .options(selectinload(NotificationJob.notification)).with_for_update()
    )
    if job is None:
        raise LookupError("Notification job not found")
    if job.status == NotificationJobStatus.SENT:
        return job
    if job.delivery_expires_at:
        expiry = job.delivery_expires_at if job.delivery_expires_at.tzinfo else job.delivery_expires_at.replace(tzinfo=timezone.utc)
        if expiry <= current:
            job.status, job.next_retry_at = NotificationJobStatus.FAILED, None
            job.last_error = "Notification delivery window expired"
            job.delivery_body = None
            db.commit(); db.refresh(job)
            return job
    if job.attempts >= settings.NOTIFICATION_RETRY_MAX_ATTEMPTS:
        job.status, job.next_retry_at = NotificationJobStatus.FAILED, None
        job.last_error = "Notification delivery retry limit reached"
        db.commit(); db.refresh(job)
        return job
    try:
        provider = notification_provider.configured_provider(job.channel)
    except notification_provider.NotificationProviderUnavailable:
        job.status, job.provider, job.next_retry_at = NotificationJobStatus.PROVIDER_UNAVAILABLE, None, None
        job.last_error = "No transactional provider is configured for this channel"
        db.commit(); db.refresh(job)
        return job
    user = db.get(User, job.notification.recipient_user_id)
    address = _recipient(user, job.channel) if user else None
    if not address:
        job.status, job.next_retry_at = NotificationJobStatus.FAILED, None
        job.last_error = "Recipient address is unavailable"
        db.commit(); db.refresh(job)
        return job
    job.provider = provider.name
    job.attempts += 1
    job.last_attempt_at = current
    try:
        result = provider.send(
            channel=job.channel, recipient=address, title=job.notification.title,
            body=job.delivery_body or job.notification.body, idempotency_key=job.idempotency_key,
        )
        job.status = NotificationJobStatus.SENT
        job.provider_message_id = result.provider_message_id[:160]
        job.sent_at = current
        job.next_retry_at = None
        job.last_error = None
        job.delivery_body = None
    except Exception:
        # Provider exception text can contain request or credential material, so
        # it is intentionally neither logged nor persisted.
        job.status = NotificationJobStatus.FAILED
        job.last_error = "External notification provider delivery failed"
        if job.attempts < settings.NOTIFICATION_RETRY_MAX_ATTEMPTS:
            delay = settings.NOTIFICATION_RETRY_BACKOFF_MINUTES * (2 ** max(0, job.attempts - 1))
            job.next_retry_at = current + timedelta(minutes=delay)
        else:
            job.next_retry_at = None
        logger.warning("Transactional notification delivery failed", extra={"notification_job_id": job.id, "channel": job.channel.value, "provider": job.provider, "attempt": job.attempts})
    db.commit(); db.refresh(job)
    return job


def run_due(db: Session, *, now: datetime | None = None, limit: int = 50) -> int:
    """Worker entry point; locks and stable provider keys make retries idempotent."""
    current = now or datetime.now(timezone.utc)
    _activate_newly_configured(db, current, limit)
    ids = list(db.scalars(
        select(NotificationJob.id).where(
            NotificationJob.status.in_((NotificationJobStatus.PENDING, NotificationJobStatus.FAILED)),
            NotificationJob.attempts < settings.NOTIFICATION_RETRY_MAX_ATTEMPTS,
            NotificationJob.next_retry_at <= current,
        ).order_by(NotificationJob.next_retry_at, NotificationJob.id).limit(limit)
    ))
    for job_id in ids:
        deliver_job(db, job_id, now=current)
    return len(ids)

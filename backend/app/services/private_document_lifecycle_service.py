"""Retryable retirement of superseded private objects."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.private_document import PrivateDocumentDeletionJob, PrivateDocumentDeletionStatus
from app.services import private_document_storage


logger = logging.getLogger(__name__)


def enqueue(db: Session, storage_key: str | None, *, reason: str, now: datetime | None = None) -> PrivateDocumentDeletionJob | None:
    if not storage_key:
        return None
    existing = db.scalar(select(PrivateDocumentDeletionJob).where(PrivateDocumentDeletionJob.storage_key == storage_key))
    if existing:
        return existing
    current = now or datetime.now(timezone.utc)
    job = PrivateDocumentDeletionJob(storage_key=storage_key, reason=reason[:200], next_retry_at=current + timedelta(days=settings.PRIVATE_DOCUMENT_REPLACEMENT_RETENTION_DAYS))
    db.add(job)
    db.flush()
    return job


def run_due(db: Session, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    stale_processing = current - timedelta(minutes=15)
    ids = list(db.scalars(select(PrivateDocumentDeletionJob.id).where(
        PrivateDocumentDeletionJob.attempts < settings.PRIVATE_DOCUMENT_DELETE_MAX_ATTEMPTS,
        or_(
            PrivateDocumentDeletionJob.status.in_((PrivateDocumentDeletionStatus.PENDING, PrivateDocumentDeletionStatus.FAILED)),
            (PrivateDocumentDeletionJob.status == PrivateDocumentDeletionStatus.PROCESSING) & (PrivateDocumentDeletionJob.updated_at <= stale_processing),
        ),
        PrivateDocumentDeletionJob.next_retry_at <= current,
    ).order_by(PrivateDocumentDeletionJob.next_retry_at).limit(50)))
    completed = 0
    for job_id in ids:
        job = db.get(PrivateDocumentDeletionJob, job_id)
        if not job:
            continue
        job.status = PrivateDocumentDeletionStatus.PROCESSING
        job.attempts += 1
        db.commit()
        try:
            private_document_storage.delete_document(job.storage_key)
        except Exception:
            db.rollback()
            job = db.get(PrivateDocumentDeletionJob, job_id)
            if not job:
                continue
            job.status = PrivateDocumentDeletionStatus.FAILED
            job.last_error = "Storage provider deletion was unavailable"
            job.next_retry_at = current + timedelta(minutes=settings.PRIVATE_DOCUMENT_DELETE_BACKOFF_MINUTES * max(1, job.attempts))
            db.commit()
            logger.warning("Private document deletion will be retried", extra={"deletion_job_id": job.id, "attempt": job.attempts})
            continue
        job = db.get(PrivateDocumentDeletionJob, job_id)
        if job:
            job.status = PrivateDocumentDeletionStatus.COMPLETED
            job.completed_at = current
            job.last_error = None
            db.commit()
            completed += 1
    return completed

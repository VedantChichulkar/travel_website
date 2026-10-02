from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token, verify_password
from app.models.auth_security import AccountActionToken, AccountTokenPurpose, AuthRateLimitBucket, AuthSession
from app.models.communication import NotificationChannel, NotificationEventType
from app.models.user import User
from app.services import notification_service


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def check_rate_limit(db: Session, *, scope: str, identifier: str, maximum: int, window: timedelta) -> None:
    """Database-backed fixed-window limit; identifiers are irreversibly keyed."""
    now = datetime.now(timezone.utc)
    key_hash = hashlib.sha256(f"{settings.SECRET_KEY}:{scope}:{identifier}".encode()).hexdigest()
    bucket = db.scalar(select(AuthRateLimitBucket).where(
        AuthRateLimitBucket.scope == scope, AuthRateLimitBucket.key_hash == key_hash
    ).with_for_update())
    if bucket is None:
        bucket = AuthRateLimitBucket(scope=scope, key_hash=key_hash, attempts=1, window_started_at=now)
        db.add(bucket)
        try:
            db.commit()
            return
        except IntegrityError:
            db.rollback()
            bucket = db.scalar(select(AuthRateLimitBucket).where(
                AuthRateLimitBucket.scope == scope, AuthRateLimitBucket.key_hash == key_hash
            ).with_for_update())
    assert bucket is not None
    if _aware(bucket.window_started_at) + window <= now:
        bucket.window_started_at, bucket.attempts = now, 1
        db.commit()
        return
    if bucket.attempts >= maximum:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many authentication attempts. Try again later.", headers={"Retry-After": str(max(1, int((_aware(bucket.window_started_at) + window - now).total_seconds())))})
    bucket.attempts += 1
    db.commit()


def create_session_tokens(db: Session, user: User) -> tuple[str, str]:
    session_id = secrets.token_hex(32)
    refresh = create_refresh_token(user, session_id)
    session = AuthSession(
        id=session_id, user_id=user.id, refresh_token_hash=hash_token(refresh),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session); db.commit()
    return create_access_token(user, session_id), refresh


def rotate_refresh_token(db: Session, user: User, session: AuthSession, presented_token: str) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    if session.revoked_at or _aware(session.expires_at) <= now or session.user_id != user.id or not secrets.compare_digest(session.refresh_token_hash, hash_token(presented_token)):
        if session.revoked_at is None:
            session.revoked_at = now
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    refresh = create_refresh_token(user, session.id)
    session.refresh_token_hash = hash_token(refresh)
    session.last_used_at = now
    db.commit()
    return create_access_token(user, session.id), refresh


def get_active_session(db: Session, *, session_id: str, user: User, token_version: int) -> AuthSession | None:
    session = db.get(AuthSession, session_id)
    if not session or session.user_id != user.id or session.revoked_at or _aware(session.expires_at) <= datetime.now(timezone.utc) or token_version != user.auth_version:
        return None
    return session


def revoke_session(db: Session, session_id: str) -> None:
    session = db.get(AuthSession, session_id)
    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_all_sessions(db: Session, user: User) -> None:
    now = datetime.now(timezone.utc)
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).values(revoked_at=now))
    user.auth_version += 1
    db.flush()


def _new_action_token(db: Session, user: User, purpose: AccountTokenPurpose, lifetime: timedelta) -> tuple[AccountActionToken, str]:
    now = datetime.now(timezone.utc)
    db.execute(update(AccountActionToken).where(
        AccountActionToken.user_id == user.id, AccountActionToken.purpose == purpose, AccountActionToken.used_at.is_(None)
    ).values(used_at=now))
    raw = secrets.token_urlsafe(32)
    record = AccountActionToken(user_id=user.id, purpose=purpose, token_hash=hash_token(raw), expires_at=now + lifetime)
    db.add(record); db.flush()
    return record, raw


def request_password_reset(db: Session, user: User | None) -> None:
    if user is None:
        # Keep the externally observable path uniform without creating orphan data.
        secrets.token_urlsafe(32)
        return
    record, raw = _new_action_token(db, user, AccountTokenPurpose.PASSWORD_RESET, timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES))
    link = f"{settings.APP_BASE_URL.rstrip('/')}/reset-password?token={raw}"
    notification_service.create(
        db, recipient_user_id=user.id, event_type=NotificationEventType.PASSWORD_RESET,
        dedupe_key=f"PASSWORD_RESET:{record.id}", title="Password reset requested",
        body="A password reset was requested for your account. Use the email link before it expires.",
        channels=(NotificationChannel.EMAIL,), external_body=f"Reset your Maharashtra Tourist Places password using this single-use link: {link}",
        delivery_expires_at=record.expires_at,
    )
    db.commit()


def reset_password(db: Session, raw_token: str, new_password: str) -> User:
    now = datetime.now(timezone.utc)
    record = db.scalar(select(AccountActionToken).where(
        AccountActionToken.token_hash == hash_token(raw_token),
        AccountActionToken.purpose == AccountTokenPurpose.PASSWORD_RESET,
    ).with_for_update())
    if not record or record.used_at or _aware(record.expires_at) <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token is invalid or expired")
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token is invalid or expired")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = now
    record.used_at = now
    revoke_all_sessions(db, user)
    notification_service.create(db, recipient_user_id=user.id, event_type=NotificationEventType.PASSWORD_CHANGED, dedupe_key=f"PASSWORD_CHANGED:reset:{record.id}", title="Password changed", body="Your Maharashtra Tourist Places password was changed and existing sessions were signed out.")
    db.commit()
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    revoke_all_sessions(db, user)
    notification_service.create(db, recipient_user_id=user.id, event_type=NotificationEventType.PASSWORD_CHANGED, dedupe_key=f"PASSWORD_CHANGED:manual:{user.auth_version}", title="Password changed", body="Your Maharashtra Tourist Places password was changed and existing sessions were signed out.")
    db.commit()


def request_email_verification(db: Session, user: User) -> None:
    if user.is_email_verified:
        return
    record, raw = _new_action_token(db, user, AccountTokenPurpose.EMAIL_VERIFICATION, timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS))
    link = f"{settings.APP_BASE_URL.rstrip('/')}/verify-email?token={raw}"
    notification_service.create(
        db, recipient_user_id=user.id, event_type=NotificationEventType.EMAIL_VERIFICATION,
        dedupe_key=f"EMAIL_VERIFICATION:{record.id}", title="Verify your email",
        body="Verify your email address using the link sent to your email.",
        channels=(NotificationChannel.EMAIL,), external_body=f"Verify your Maharashtra Tourist Places email using this single-use link: {link}",
        delivery_expires_at=record.expires_at,
    )
    db.commit()


def verify_email(db: Session, raw_token: str) -> User:
    now = datetime.now(timezone.utc)
    record = db.scalar(select(AccountActionToken).where(
        AccountActionToken.token_hash == hash_token(raw_token),
        AccountActionToken.purpose == AccountTokenPurpose.EMAIL_VERIFICATION,
    ).with_for_update())
    if not record or record.used_at or _aware(record.expires_at) <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token is invalid or expired")
    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token is invalid or expired")
    record.used_at = now
    user.is_email_verified = True
    user.email_verified_at = now
    db.commit(); db.refresh(user)
    return user

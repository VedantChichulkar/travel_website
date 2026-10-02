from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import SessionLocal
from app.models.user import User, UserStatus
from app.repositories.user_repository import get_user_by_id
from app.services import auth_security_service


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _authentication_error(detail: str = "Could not validate credentials") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _user_from_token(token: str, db: Session) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise _authentication_error("Invalid token type")
        user_id = int(payload["sub"])
        session_id = str(payload["sid"])
        token_version = int(payload["ver"])
    except ExpiredSignatureError as exc:
        raise _authentication_error("Token has expired") from exc
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise _authentication_error() from exc

    user = get_user_by_id(db, user_id)
    if user is None:
        raise _authentication_error()
    if not user.is_active or user.status != UserStatus.ACTIVE:
        raise _authentication_error("Account is inactive or suspended")
    if auth_security_service.get_active_session(db, session_id=session_id, user=user, token_version=token_version) is None:
        raise _authentication_error("Session is no longer active")
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return _user_from_token(token, db)


def get_optional_user(token: str | None = Depends(optional_oauth2_scheme), db: Session = Depends(get_db)) -> User | None:
    return _user_from_token(token, db) if token else None

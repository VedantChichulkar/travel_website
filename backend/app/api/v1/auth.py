from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import ExpiredSignatureError, JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token
from app.dependencies import get_current_user, get_db
from app.models.user import User, UserStatus
from app.repositories.user_repository import get_user_by_id
from app.schemas.auth import (
    AccessTokenResponse,
    BrowserSessionResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    ActionTokenRequest,
    GenericMessageResponse,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import authenticate_user, register_user
from app.services import auth_security_service
from app.repositories.user_repository import get_user_by_email


router = APIRouter()


def _client_key(request: Request, identity: str = "") -> str:
    host = request.client.host if request.client else "unknown"
    return f"{host}:{identity.strip().lower()}"


def _build_token_response(db: Session, user: User) -> TokenResponse:
    access_token, refresh_token = auth_security_service.create_session_tokens(db, user)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/api/v1/auth",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, request: Request, db: Session = Depends(get_db)) -> UserResponse:
    auth_security_service.check_rate_limit(db, scope="register", identifier=_client_key(request), maximum=settings.AUTH_REGISTER_RATE_LIMIT, window=timedelta(hours=1))
    return register_user(db, data)


@router.post("/login", response_model=BrowserSessionResponse)
def login(data: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)) -> BrowserSessionResponse:
    auth_security_service.check_rate_limit(db, scope="login", identifier=_client_key(request, str(data.email)), maximum=settings.AUTH_LOGIN_RATE_LIMIT, window=timedelta(minutes=1))
    user = authenticate_user(db, str(data.email), data.password, portal=data.portal)
    tokens = _build_token_response(db, user)
    _set_refresh_cookie(response, tokens.refresh_token)
    return BrowserSessionResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=tokens.user,
    )


@router.post("/token", response_model=TokenResponse)
def oauth2_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    auth_security_service.check_rate_limit(db, scope="oauth-token", identifier=_client_key(request, form_data.username), maximum=settings.AUTH_LOGIN_RATE_LIMIT, window=timedelta(minutes=1))
    user = authenticate_user(db, form_data.username, form_data.password)
    return _build_token_response(db, user)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    data: RefreshTokenRequest,
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        refresh_token = data.refresh_token if data and data.refresh_token else refresh_cookie
        if not refresh_token:
            raise credentials_error
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_error
        user_id = int(payload["sub"])
        session_id = str(payload["sid"])
        token_version = int(payload["ver"])
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise credentials_error from exc

    user = get_user_by_id(db, user_id)
    if user is None or not user.is_active or user.status != UserStatus.ACTIVE:
        raise credentials_error
    session = auth_security_service.get_active_session(db, session_id=session_id, user=user, token_version=token_version)
    if session is None:
        raise credentials_error
    access_token, rotated_refresh = auth_security_service.rotate_refresh_token(db, user, session, refresh_token)
    _set_refresh_cookie(response, rotated_refresh)
    return AccessTokenResponse(
        access_token=access_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, refresh_cookie: str | None = Cookie(default=None, alias=settings.AUTH_COOKIE_NAME), db: Session = Depends(get_db)) -> None:
    if refresh_cookie:
        try:
            payload = decode_token(refresh_cookie)
            if payload.get("type") == "refresh":
                auth_security_service.revoke_session(db, str(payload["sid"]))
        except (JWTError, KeyError, TypeError, ValueError):
            pass
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        domain=settings.AUTH_COOKIE_DOMAIN,
        path="/api/v1/auth",
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


@router.post("/forgot-password", response_model=GenericMessageResponse)
def forgot_password(data: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)) -> GenericMessageResponse:
    auth_security_service.check_rate_limit(db, scope="password-recovery", identifier=_client_key(request, str(data.email)), maximum=settings.AUTH_RECOVERY_RATE_LIMIT, window=timedelta(hours=1))
    auth_security_service.request_password_reset(db, get_user_by_email(db, str(data.email)))
    return GenericMessageResponse(message="If an account exists, password reset instructions have been sent.")


@router.post("/reset-password", response_model=GenericMessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)) -> GenericMessageResponse:
    auth_security_service.reset_password(db, data.token, data.new_password)
    return GenericMessageResponse(message="Password reset completed. Sign in again on your account portal.")


@router.post("/change-password", response_model=GenericMessageResponse)
def change_password(data: ChangePasswordRequest, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GenericMessageResponse:
    auth_security_service.change_password(db, user, data.current_password, data.new_password)
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, domain=settings.AUTH_COOKIE_DOMAIN, path="/api/v1/auth", secure=settings.AUTH_COOKIE_SECURE, httponly=True, samesite=settings.AUTH_COOKIE_SAMESITE)
    return GenericMessageResponse(message="Password changed. All sessions have been signed out.")


@router.post("/email-verification/request", response_model=GenericMessageResponse)
def request_email_verification(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> GenericMessageResponse:
    auth_security_service.check_rate_limit(db, scope="email-verification", identifier=_client_key(request, user.email), maximum=settings.AUTH_RECOVERY_RATE_LIMIT, window=timedelta(hours=1))
    auth_security_service.request_email_verification(db, user)
    return GenericMessageResponse(message="If verification is needed, a new email has been sent.")


@router.post("/email-verification/confirm", response_model=UserResponse)
def confirm_email_verification(data: ActionTokenRequest, db: Session = Depends(get_db)) -> UserResponse:
    return UserResponse.model_validate(auth_security_service.verify_email(db, data.token))

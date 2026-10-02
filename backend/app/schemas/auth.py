import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.user import UserResponse


def _strong_password(value: str) -> str:
    if len(value.encode("utf-8")) > 72 or not re.search(r"[a-z]", value) or not re.search(r"[A-Z]", value) or not re.search(r"\d", value):
        raise ValueError("password must be at most 72 UTF-8 bytes and contain uppercase, lowercase, and a number")
    return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    portal: UserRole | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class BrowserSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ActionTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=512)


class ResetPasswordRequest(ActionTokenRequest):
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _strong_password(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _strong_password(value)


class GenericMessageResponse(BaseModel):
    message: str

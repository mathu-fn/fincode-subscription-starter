from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _normalize_email(value: str) -> str:
    # メールは大文字小文字を区別しない前提で扱う。trim + 小文字化して保存・照合し、
    # ``Alice@x.com`` と ``alice@x.com`` が別アカウント・ログイン不一致になるのを防ぐ。
    return value.strip().lower()


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=255)

    @field_validator("email", mode="after")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _normalize_email(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=255)

    @field_validator("email", mode="after")
    @classmethod
    def _normalize(cls, value: str) -> str:
        return _normalize_email(value)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut


class MessageResponse(BaseModel):
    message: str


class SessionStatusResponse(BaseModel):
    authenticated: bool
    user: UserOut | None = None

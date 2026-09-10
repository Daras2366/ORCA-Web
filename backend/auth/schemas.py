"""
schemas.py — Pydantic v2 request/response schemas for the Auth API.

password_hash is NEVER included in response schemas.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.auth.models import ALLOWED_USER_TYPES

UserTypeEnum = Literal[
    "fisherman",
    "coast_guard",
    "researcher",
    "maritime_operator",
    "coastal_authority",
    "other",
]


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    user_type: UserTypeEnum = "other"
    preferred_language: str = Field(default="en", max_length=10)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match.")
        return v

    @field_validator("user_type")
    @classmethod
    def valid_user_type(cls, v: str) -> str:
        if v not in ALLOWED_USER_TYPES:
            raise ValueError(
                f"user_type must be one of: {', '.join(ALLOWED_USER_TYPES)}"
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserOut(BaseModel):
    """Safe user representation — never includes password_hash."""

    id: str
    name: str
    email: str
    user_type: str
    preferred_language: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageResponse(BaseModel):
    message: str

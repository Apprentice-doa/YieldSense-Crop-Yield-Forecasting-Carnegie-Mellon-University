"""Authentication request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from typing import Optional


class LoginRequest(BaseModel):
    """Farmer login credentials using either email or phone number."""

    email_address: Optional[str] = Field(default=None, min_length=5)
    phone_number: Optional[str] = Field(default=None, min_length=7)
    password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def require_one_contact_method(self):
        if bool(self.email_address) == bool(self.phone_number):
            raise ValueError("Provide exactly one of email_address or phone_number")
        return self


class TokenResponse(BaseModel):
    """JWT token response after successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    session_id: str


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""

    refresh_token: str = Field(..., min_length=10)


class SessionStatusResponse(BaseModel):
    """Response showing session status."""

    session_id: str
    farmer_id: int
    is_active: bool
    access_token_expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

"""Authentication request and response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field
from datetime import datetime


class LoginRequest(BaseModel):
    """Farmer login credentials."""

    email_address: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)


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
        orm_mode = True

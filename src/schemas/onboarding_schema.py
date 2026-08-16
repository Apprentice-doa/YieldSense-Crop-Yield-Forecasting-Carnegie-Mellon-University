"""Request and response schemas for farmer onboarding."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CropProfileCreateOB(BaseModel):
    """Crop profile data during onboarding."""

    crop_type: str
    planting_month: str
    harvest_month: str
    average_yield_tons: float


class OnboardingRequest(BaseModel):
    """Farmer onboarding request payload."""

    name: str = Field(..., min_length=1)
    farm_country: str = Field(..., min_length=1)
    farm_state_region: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=7)
    email_address: str = Field(..., min_length=5)
    area_of_farmland: float = Field(..., gt=0)
    password: str = Field(..., min_length=8)
    crop_profiles: List[CropProfileCreateOB] = Field(..., min_items=1)


class EmailVerificationRequest(BaseModel):
    """Email verification request with OTP."""

    farmer_id: int
    otp: str = Field(..., min_length=6, max_length=6)


class FarmerOnboardingResponse(BaseModel):
    """Response after successful onboarding."""

    id: int
    name: str
    email_address: str
    phone_number: str
    farm_country: str
    farm_state_region: str
    area_of_farmland: float
    is_verified: bool
    otp_verified: bool
    created_at: datetime

    class Config:
        orm_mode = True

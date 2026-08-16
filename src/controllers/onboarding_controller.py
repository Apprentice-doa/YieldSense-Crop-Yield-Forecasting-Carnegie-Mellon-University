"""Onboarding controller for farmer account creation and verification."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.onboarding_service import OnboardingService
from src.schemas.onboarding_schema import (
    OnboardingRequest,
    EmailVerificationRequest,
    FarmerOnboardingResponse,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/signup", response_model=FarmerOnboardingResponse)
async def signup(
    payload: OnboardingRequest, db: Session = Depends(get_db)
) -> FarmerOnboardingResponse:
    """Register a new farmer account with email and password.
    
    - Requires farmer details (name, contact, farm info)
    - Requires at least one crop profile
    - Password must be at least 8 characters
    - Email and phone must be unique
    - Returns farmer details (not yet verified until OTP is confirmed)
    """
    svc = OnboardingService(db)
    try:
        farmer = svc.create_farmer_account(payload.model_dump())
    except ValueError as e:
        if str(e) == "email_exists":
            raise HTTPException(status_code=400, detail="Email already registered")
        if str(e) == "phone_exists":
            raise HTTPException(status_code=400, detail="Phone number already registered")
        raise

    return farmer


@router.post("/verify-email")
async def verify_email(
    payload: EmailVerificationRequest, db: Session = Depends(get_db)
) -> dict:
    """Verify farmer email using static OTP.
    
    - OTP is: 123456 (static for development)
    - After verification, farmer account is active
    - Farmer can then log in with email and password
    """
    svc = OnboardingService(db)
    try:
        farmer = svc.verify_email_with_otp(payload.farmer_id, payload.otp)
    except ValueError as e:
        if str(e) == "invalid_otp":
            raise HTTPException(status_code=400, detail="Invalid OTP")
        raise

    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    return {
        "status": "success",
        "message": "Email verified successfully. You can now log in.",
        "farmer_id": farmer.id,
        "email": farmer.email_address,
        "is_verified": farmer.is_verified,
    }


@router.get("/status/{farmer_id}")
async def check_status(farmer_id: int, db: Session = Depends(get_db)) -> dict:
    """Check the onboarding status of a farmer.
    
    Returns verification status for email and OTP.
    """
    svc = OnboardingService(db)
    status = svc.check_onboarding_status(farmer_id)

    if not status:
        raise HTTPException(status_code=404, detail="Farmer not found")

    return status

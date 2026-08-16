"""Onboarding service for farmer account creation and verification."""

from __future__ import annotations

from sqlalchemy.orm import Session
from typing import List

from src.db.models.farmer import Farmer
from src.db.models.crop_profile import CropProfile
from src.repositories.farmer_repository import FarmerRepository
from src.utils.auth import hash_password, verify_otp


class OnboardingService:
    """Service for managing farmer onboarding and account verification."""

    def __init__(self, db: Session):
        self.repo = FarmerRepository(db)
        self.db = db

    def create_farmer_account(self, payload: dict) -> Farmer:
        """Create a new farmer account during onboarding.
        
        Args:
            payload: Dictionary containing farmer and crop profile data
            
        Returns:
            Farmer object (not yet verified)
            
        Raises:
            ValueError: If email or phone already exists
        """
        email = payload.get("email_address")
        phone = payload.get("phone_number")
        password = payload.get("password")

        # Check for existing email/phone
        existing_email = self.repo.find_by_email(email)
        if existing_email:
            raise ValueError("email_exists")

        existing_phone = self.repo.find_by_phone(phone)
        if existing_phone:
            raise ValueError("phone_exists")

        # Create farmer with hashed password
        password_hash = hash_password(password)
        farmer = Farmer(
            name=payload.get("name"),
            farm_country=payload.get("farm_country"),
            farm_state_region=payload.get("farm_state_region"),
            phone_number=phone,
            email_address=email,
            area_of_farmland=payload.get("area_of_farmland", 0.0),
            password_hash=password_hash,
            is_verified=False,
            otp_verified=False,
        )
        self.repo.create(farmer)

        # Add crop profiles
        for cp in payload.get("crop_profiles", []):
            crop = CropProfile(
                farmer_id=farmer.id,
                crop_type=cp.get("crop_type"),
                planting_month=cp.get("planting_month"),
                harvest_month=cp.get("harvest_month"),
                average_yield_tons=cp.get("average_yield_tons", 0.0),
            )
            self.db.add(crop)

        self.repo.commit()
        return farmer

    def verify_email_with_otp(self, farmer_id: int, otp: str) -> Farmer | None:
        """Verify farmer email using the provided OTP.
        
        Args:
            farmer_id: ID of the farmer to verify
            otp: OTP string to verify
            
        Returns:
            Updated Farmer object if verification successful, None if farmer not found
            
        Raises:
            ValueError: If OTP is invalid
        """
        farmer = self.repo.get_by_id(farmer_id)
        if not farmer:
            return None

        if not verify_otp(otp):
            raise ValueError("invalid_otp")

        # Mark as OTP verified (email verification complete)
        farmer.otp_verified = True
        farmer.is_verified = True

        self.db.flush()
        self.repo.commit()
        return farmer

    def check_onboarding_status(self, farmer_id: int) -> dict | None:
        """Check the onboarding status of a farmer.
        
        Returns:
            Dictionary with verification status or None if farmer not found
        """
        farmer = self.repo.get_by_id(farmer_id)
        if not farmer:
            return None

        return {
            "farmer_id": farmer.id,
            "email_address": farmer.email_address,
            "is_verified": farmer.is_verified,
            "otp_verified": farmer.otp_verified,
        }

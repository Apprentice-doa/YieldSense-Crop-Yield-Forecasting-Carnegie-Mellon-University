"""Farmer onboarding API controller.

This file is intentionally a placeholder for the first domain-specific API
module, keeping the route layer separated from future service/repository logic.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/farmers", tags=["farmers"])


class CropProfileCreate(BaseModel):
    """A single crop profile that can be attached to a farmer."""

    crop_type: str
    planting_month: str
    harvest_month: str
    average_yield_tons: float


class FarmerOnboardingCreate(BaseModel):
    """Farmer onboarding payload expected by the API."""

    name: str
    farm_country: str
    farm_state_region: str
    phone_number: str
    area_of_farmland: float
    email_address: Optional[str] = None
    crop_profiles: List[CropProfileCreate]


@router.get("")
async def list_farmers() -> dict:
    """List all farmer records."""

    return {"items": []}


@router.post("")
async def create_farmer(payload: FarmerOnboardingCreate) -> dict:
    """Create a new farmer onboarding record."""

    return {
        "message": "farmer onboarding payload accepted",
        "farmer": {
            "name": payload.name,
            "farm_country": payload.farm_country,
            "farm_state_region": payload.farm_state_region,
            "phone_number": payload.phone_number,
            "email_address": payload.email_address,
            "area_of_farmland": payload.area_of_farmland,
            "crop_profiles": [profile.model_dump() for profile in payload.crop_profiles],
        },
    }


@router.get("/{farmer_id}")
async def get_farmer(farmer_id: int) -> dict:
    """Fetch a farmer profile by identifier."""

    raise HTTPException(status_code=501, detail="Farmer retrieval is still under implementation")


@router.put("/{farmer_id}")
async def update_farmer(farmer_id: int) -> dict:
    """Update a farmer profile and associated crop records."""

    raise HTTPException(status_code=501, detail="Farmer update is still under implementation")


@router.delete("/{farmer_id}")
async def delete_farmer(farmer_id: int) -> dict:
    """Delete a farmer profile and associated records."""

    raise HTTPException(status_code=501, detail="Farmer deletion is still under implementation")

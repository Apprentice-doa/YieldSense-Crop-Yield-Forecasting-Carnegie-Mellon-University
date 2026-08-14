"""Farmer onboarding API controller.

This file is intentionally a placeholder for the first domain-specific API
module, keeping the route layer separated from future service/repository logic.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.farmer_service import FarmerService
from src.schemas.farmer_schema import FarmerOut

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


class FarmerOnboardingUpdate(BaseModel):
    name: Optional[str] = None
    farm_country: Optional[str] = None
    farm_state_region: Optional[str] = None
    phone_number: Optional[str] = None
    area_of_farmland: Optional[float] = None
    email_address: Optional[str] = None
    crop_profiles: Optional[List[CropProfileCreate]] = None


@router.get("", response_model=List[FarmerOut])
async def list_farmers(db: Session = Depends(get_db)) -> List[FarmerOut]:
    """List all farmer records."""

    svc = FarmerService(db)
    farmers = svc.list_farmers()
    return farmers


@router.post("", response_model=FarmerOut)
async def create_farmer(payload: FarmerOnboardingCreate, db: Session = Depends(get_db)) -> FarmerOut:
    """Create a new farmer onboarding record."""

    svc = FarmerService(db)
    farmer = svc.create_farmer(payload.model_dump())
    return farmer


@router.get("/{farmer_id}", response_model=FarmerOut)
async def get_farmer(farmer_id: int, db: Session = Depends(get_db)) -> FarmerOut:
    """Fetch a farmer profile by identifier."""

    svc = FarmerService(db)
    farmer = svc.get_farmer(farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer


@router.put("/{farmer_id}", response_model=FarmerOut)
async def update_farmer(farmer_id: int, payload: FarmerOnboardingUpdate, db: Session = Depends(get_db)) -> FarmerOut:
    """Update a farmer profile and associated crop records."""

    svc = FarmerService(db)
    try:
        farmer = svc.update_farmer(farmer_id, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        if str(e) == "phone_exists":
            raise HTTPException(status_code=400, detail="Phone number already in use")
        if str(e) == "email_exists":
            raise HTTPException(status_code=400, detail="Email address already in use")
        raise

    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer


@router.delete("/{farmer_id}")
async def delete_farmer(farmer_id: int, db: Session = Depends(get_db)) -> dict:
    """Delete a farmer profile and associated records."""

    svc = FarmerService(db)
    ok = svc.delete_farmer(farmer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return {"deleted": True}

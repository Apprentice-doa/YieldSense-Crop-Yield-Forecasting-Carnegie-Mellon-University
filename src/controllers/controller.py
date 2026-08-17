from __future__ import annotations
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.services.farmer_service import FarmerService
from src.utils.security import AuthenticatedFarmer, get_current_farmer, require_farmer_access
from models.request import FarmerOnboardingCreate, FarmerOnboardingUpdate
from models.response import FarmerOut

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@router.get("/farmers", response_model=List[FarmerOut])
async def list_farmers(
    db: Session = Depends(get_db),
    _: AuthenticatedFarmer = Depends(get_current_farmer),
) -> List[FarmerOut]:
    return FarmerService(db).list_farmers()

@router.post("/farmers", response_model=FarmerOut)
async def create_farmer(
    payload: FarmerOnboardingCreate,
    db: Session = Depends(get_db),
    _: AuthenticatedFarmer = Depends(get_current_farmer),
) -> FarmerOut:
    return FarmerService(db).create_farmer(payload.model_dump())

@router.get("/farmers/{farmer_id}", response_model=FarmerOut)
async def get_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> FarmerOut:
    require_farmer_access(farmer_id, current)
    farmer = FarmerService(db).get_farmer(farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@router.put("/farmers/{farmer_id}", response_model=FarmerOut)
async def update_farmer(
    farmer_id: int,
    payload: FarmerOnboardingUpdate,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> FarmerOut:
    require_farmer_access(farmer_id, current)
    try:
        farmer = FarmerService(db).update_farmer(farmer_id, payload.model_dump(exclude_unset=True))
    except ValueError as e:
        if str(e) == "phone_exists":
            raise HTTPException(status_code=400, detail="Phone number already in use")
        if str(e) == "email_exists":
            raise HTTPException(status_code=400, detail="Email address already in use")
        raise
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@router.delete("/farmers/{farmer_id}")
async def delete_farmer(
    farmer_id: int,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> dict:
    require_farmer_access(farmer_id, current)
    if not FarmerService(db).delete_farmer(farmer_id):
        raise HTTPException(status_code=404, detail="Farmer not found")
    return {"deleted": True}


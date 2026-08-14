from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional


class CropProfileOut(BaseModel):
    id: int
    crop_type: str
    planting_month: str
    harvest_month: str
    average_yield_tons: float


class FarmerOut(BaseModel):
    id: int
    name: str
    farm_country: str
    farm_state_region: str
    phone_number: str
    email_address: Optional[str]
    area_of_farmland: float
    crop_profiles: List[CropProfileOut] = []

    class Config:
        orm_mode = True


class FarmerUpdate(BaseModel):
    name: Optional[str] = None
    farm_country: Optional[str] = None
    farm_state_region: Optional[str] = None
    phone_number: Optional[str] = None
    email_address: Optional[str] = None
    area_of_farmland: Optional[float] = None
    crop_profiles: Optional[List[CropProfileOut]] = None

    class Config:
        orm_mode = True

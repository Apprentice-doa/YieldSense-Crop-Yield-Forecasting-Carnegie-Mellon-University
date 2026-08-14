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

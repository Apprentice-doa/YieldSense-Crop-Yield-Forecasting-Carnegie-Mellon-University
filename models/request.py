from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from pydantic import BaseModel

@dataclass
class YieldPredictionContext:
    farmer_name: str
    crop_type: str
    farm_location: str
    season: str
    harvest_date: str
    predicted_yield_kg_per_ha: float
    farm_size_ha: float
    soil_type: Optional[str] = None
    irrigation_method: Optional[str] = None

    @property
    def total_yield_kg(self) -> float:
        return self.predicted_yield_kg_per_ha * self.farm_size_ha

    @property
    def yield_category(self) -> str:
        if self.predicted_yield_kg_per_ha >= 4000:
            return "high"
        elif self.predicted_yield_kg_per_ha >= 2000:
            return "moderate"
        return "low"

class CropProfileCreate(BaseModel):
    crop_type: str
    planting_month: str
    harvest_month: str
    average_yield_tons: float

class FarmerOnboardingCreate(BaseModel):
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

class ChatRequest(BaseModel):
    session_id: str
    farmer_id: int
    message: str
    conversation_id: Optional[str] = None

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date
from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}


class ChatResponse(BaseModel):
    message: str
    language: str
    session_id: str
    conversation_id: str
    message_id: str
    chart: Optional[Dict[str, Any]] = None


class YieldRecordOut(BaseModel):
    id: int
    farmer_id: int
    crop_type: str
    season: str
    harvest_date: Optional[date] = None
    predicted_yield_kg_per_ha: float
    actual_yield_kg_per_ha: Optional[float] = None
    advisory_summary: Optional[str] = None
    created_at: Optional[date] = None

    model_config = {"from_attributes": True}


class AdvisoryOut(BaseModel):
    id: int
    farmer_id: int
    crop_type: str
    season: str
    predicted_yield_kg_per_ha: float
    actual_yield_kg_per_ha: Optional[float] = None
    advisory_summary: Optional[str] = None

    model_config = {"from_attributes": True}


class PredictionResponse(BaseModel):
    record_id: int = Field(..., description="ID of the saved YieldRecord")
    predicted_yield: float = Field(..., description="Predicted yield (model units)")
    advisory_summary: str = Field(..., description="LLM-generated advisory summary")

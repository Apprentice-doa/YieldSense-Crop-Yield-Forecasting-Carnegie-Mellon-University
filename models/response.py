from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

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

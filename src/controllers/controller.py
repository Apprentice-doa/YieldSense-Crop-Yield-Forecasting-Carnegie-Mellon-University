from __future__ import annotations
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.services.farmer_service import FarmerService
from src.services.chat_service import chat, new_conversation
from models.request import FarmerOnboardingCreate, FarmerOnboardingUpdate, ChatRequest
from models.response import ChatResponse, FarmerOut

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, str]:
    return {"status": "healthy"}

@router.get("/farmers", response_model=List[FarmerOut])
async def list_farmers(db: Session = Depends(get_db)) -> List[FarmerOut]:
    return FarmerService(db).list_farmers()

@router.post("/farmers", response_model=FarmerOut)
async def create_farmer(payload: FarmerOnboardingCreate, db: Session = Depends(get_db)) -> FarmerOut:
    return FarmerService(db).create_farmer(payload.model_dump())

@router.get("/farmers/{farmer_id}", response_model=FarmerOut)
async def get_farmer(farmer_id: int, db: Session = Depends(get_db)) -> FarmerOut:
    farmer = FarmerService(db).get_farmer(farmer_id)
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")
    return farmer

@router.put("/farmers/{farmer_id}", response_model=FarmerOut)
async def update_farmer(farmer_id: int, payload: FarmerOnboardingUpdate, db: Session = Depends(get_db)) -> FarmerOut:
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
async def delete_farmer(farmer_id: int, db: Session = Depends(get_db)) -> dict:
    if not FarmerService(db).delete_farmer(farmer_id):
        raise HTTPException(status_code=404, detail="Farmer not found")
    return {"deleted": True}

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    return chat(
        session_id=payload.session_id,
        farmer_id=payload.farmer_id,
        user_message=payload.message,
        db=db,
        conversation_id=payload.conversation_id,
    )

@router.post("/chat/new-conversation")
async def new_conversation_endpoint(session_id: str) -> dict:
    try:
        return {"conversation_id": new_conversation(session_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

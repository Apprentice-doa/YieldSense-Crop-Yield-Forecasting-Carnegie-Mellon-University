"""API controllers and endpoints."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from .service import MLService
from models.request_models import PredictionRequest
from models.response_models import PredictionResponse

router = APIRouter()
ml_service = MLService()

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest) -> PredictionResponse:
    """Make prediction using ML model."""
    try:
        result = await ml_service.predict(request.data)
        return PredictionResponse(prediction=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
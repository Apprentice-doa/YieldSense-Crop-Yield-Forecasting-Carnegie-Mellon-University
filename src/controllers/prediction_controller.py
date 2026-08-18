"""Prediction controller — POST /predict."""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.request import PredictionRequest
from models.response import PredictionResponse
from src.db.session import get_db
from src.services.prediction_service import predict_and_save
from src.utils.security import AuthenticatedFarmer, get_current_farmer, require_farmer_access

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
def predict_yield(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> PredictionResponse:
    """Run ML inference, generate advisory summary, persist and return result."""
    require_farmer_access(payload.farmer_id, current)
    try:
        record = predict_and_save(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Farmer not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return PredictionResponse(
        record_id=record.id,
        predicted_yield=record.predicted_yield_kg_per_ha,
        advisory_summary=record.advisory_summary,
    )

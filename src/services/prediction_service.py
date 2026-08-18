from __future__ import annotations
import os
from datetime import date
from pathlib import Path
import joblib
import pandas as pd
from sqlalchemy.orm import Session
from models.request import YieldPredictionContext
from src.db.models.yield_record import YieldRecord
from src.repositories.farmer_repository import FarmerRepository
from src.repositories.yield_record_repository import YieldRecordRepository
from src.services.summary_service import get_summary

_MODEL_DIR = Path(__file__).resolve().parents[2] / "data" / "model_registry"
_DEFAULT_MODEL = "histgbm_model.joblib"

_SEASON_MAP = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

_HARVEST_SEASON_MAP = {
    3: "Long Rains", 4: "Long Rains", 5: "Long Rains",
    6: "Long Rains", 7: "Long Rains", 8: "Long Rains",
    9: "Short Rains", 10: "Short Rains", 11: "Short Rains",
    12: "Short Rains", 1: "Short Rains", 2: "Short Rains",
}


def _derive_season(harvest_date: str) -> str:
    dt = date.fromisoformat(harvest_date)
    return f"{_HARVEST_SEASON_MAP[dt.month]} {dt.year}"

_FEATURE_COLS = [
    "GNDVI", "NDVI", "NDWI", "SAVI",
    "crop_type", "latitude", "longitude",
    "rainfall", "soil_moisture", "temperature",
    "year", "month", "day", "season",
]

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        model_name = os.environ.get("YIELD_MODEL", _DEFAULT_MODEL)
        _pipeline = joblib.load(_MODEL_DIR / model_name)
    return _pipeline


def _ml_predict(payload) -> tuple[float, date]:
    """Run the ML model and return (predicted_yield, parsed_date)."""
    dt = pd.to_datetime(payload.date_of_image)
    row = {
        "GNDVI": payload.gndvi,
        "NDVI": payload.ndvi,
        "NDWI": payload.ndwi,
        "SAVI": payload.savi,
        "crop_type": payload.crop_type,
        "latitude": payload.latitude,
        "longitude": payload.longitude,
        "rainfall": payload.rainfall,
        "soil_moisture": payload.soil_moisture,
        "temperature": payload.temperature,
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
        "season": _SEASON_MAP[dt.month],
    }
    df = pd.DataFrame([row], columns=_FEATURE_COLS)
    return float(_get_pipeline().predict(df)[0]), dt.date()


def predict_and_save(payload, db: Session) -> YieldRecord:
    farmer_repo = FarmerRepository(db)
    record_repo = YieldRecordRepository(db)
    farmer = farmer_repo.get_by_id(payload.farmer_id)
    if not farmer:
        raise ValueError("farmer_not_found")

    predicted_yield, image_date = _ml_predict(payload)
    season = _derive_season(payload.harvest_date)
    ctx = YieldPredictionContext(
        farmer_name=farmer.name,
        crop_type=payload.crop_type,
        farm_location=f"{farmer.farm_state_region}, {farmer.farm_country}",
        season=season,
        harvest_date=payload.harvest_date,
        predicted_yield_kg_per_ha=predicted_yield,
        farm_size_ha=payload.farm_size_ha,
    )
    summary = get_summary(ctx)

    record = YieldRecord(
        farmer_id=farmer.id,
        crop_type=payload.crop_type,
        season=season,
        harvest_date=date.fromisoformat(payload.harvest_date),
        predicted_yield_kg_per_ha=predicted_yield,
        advisory_summary=summary,
    )
    record_repo.create(record)
    record_repo.commit()
    return record

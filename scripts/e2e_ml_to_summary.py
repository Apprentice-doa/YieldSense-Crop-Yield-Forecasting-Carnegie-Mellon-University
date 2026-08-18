"""End-to-end test: ML inference → season derivation → LLM advisory summary."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from models.request import YieldPredictionContext
from src.services.prediction_service import _ml_predict, _derive_season
from src.services.summary_service import get_summary


class _Payload:
    farmer_id = 1
    crop_type = "Rice"
    harvest_date = "2025-08-15"
    farm_size_ha = 2.5
    date_of_image = "2025-06-01"
    gndvi = 0.3747
    ndvi = 0.3618
    ndwi = -0.3747
    savi = 0.5426
    latitude = 20.952
    longitude = 78.0463
    rainfall = 9.562
    soil_moisture = 28.2305
    temperature = 19.9091


payload = _Payload()

print("=== ML Inference ===")
predicted_yield, image_date = _ml_predict(payload)
print(f"Predicted yield : {predicted_yield:.2f} kg/ha")
print(f"Image date      : {image_date}")

season = _derive_season(payload.harvest_date)
print(f"Derived season  : {season}")

ctx = YieldPredictionContext(
    farmer_name="John Kamau",
    crop_type=payload.crop_type,
    farm_location="Nakuru, Kenya",
    season=season,
    harvest_date=payload.harvest_date,
    predicted_yield_kg_per_ha=predicted_yield,
    farm_size_ha=payload.farm_size_ha,
)

print(f"\nYield category  : {ctx.yield_category}")
print(f"Total yield     : {ctx.total_yield_kg:,.0f} kg")

print("\n=== LLM Advisory Summary ===")
summary = get_summary(ctx)
print(summary)

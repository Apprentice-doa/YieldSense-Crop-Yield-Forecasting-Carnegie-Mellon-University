from dataclasses import dataclass
from typing import Optional

@dataclass
class YieldPredictionContext:
    farmer_name: str
    crop_type: str
    farm_location: str
    season: str                      # e.g. "Spring 2025", "Dry Season 2024"
    harvest_date: str                # e.g. "October 2025"
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

    
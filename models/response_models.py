from pydantic import BaseModel
from typing import List, Any


class PredictionResponse(BaseModel):
    """Minimal prediction response wrapper used by the controller."""

    prediction: List[Any]

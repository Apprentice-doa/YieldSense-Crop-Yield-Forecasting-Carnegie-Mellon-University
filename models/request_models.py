from pydantic import BaseModel
from typing import List, Any


class PredictionRequest(BaseModel):
    """Generic prediction request expected by the legacy controller.

    The real prediction API will be extended later with feature names and
    domain-aware schemas. For now keep a minimal contract used by
    `src/controller.py`.
    """

    data: List[Any]

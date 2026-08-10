"""Business logic services."""

import joblib
import numpy as np
from typing import Any, List
from pathlib import Path

class MLService:
    """Machine learning service for predictions."""
    
    def __init__(self):
        self.model = None
        self.model_path = Path("artefacts/model.pkl")
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the trained model."""
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
        else:
            raise FileNotFoundError(f"Model not found at {self.model_path}")
    
    async def predict(self, data: List[Any]) -> List[float]:
        """Make predictions on input data."""
        if self.model is None:
            raise ValueError("Model not loaded")
        
        # Convert to numpy array
        input_array = np.array(data).reshape(1, -1)
        
        # Make prediction
        prediction = self.model.predict(input_array)
        
        return prediction.tolist()
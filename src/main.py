"""Main application entry point."""
import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from src.controllers.controller import router

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


app = FastAPI(
    title="YieldSense API",
    description="Crop yield forecasting and farmer onboarding API service",
    version="0.1.0",
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

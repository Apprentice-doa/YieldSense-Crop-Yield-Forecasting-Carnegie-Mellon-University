"""Main application entry point."""

import sys
from pathlib import Path

# Ensure the project root is on sys.path so the `src` package can be
# imported whether the process is started from the project root or
# from inside the `src/` directory (helps with `python -m uvicorn ...`).
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import uvicorn
from fastapi import FastAPI

from src.controllers.health_controller import router as health_router
from src.controllers.farmers_controller import router as farmers_router

app = FastAPI(
    title="YieldSense API",
    description="Crop yield forecasting and farmer onboarding API service",
    version="0.1.0"
    ,
    # Explicitly expose OpenAPI/Swagger and ReDoc at their default paths.
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(health_router)
app.include_router(farmers_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

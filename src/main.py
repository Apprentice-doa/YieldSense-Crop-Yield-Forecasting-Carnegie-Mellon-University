"""Main application entry point."""

import uvicorn
from fastapi import FastAPI

from .controller import router
from src.controllers.health_controller import router as health_router
from src.controllers.farmers_controller import router as farmers_router

app = FastAPI(
    title="YieldSense API",
    description="Crop yield forecasting and farmer onboarding API service",
    version="0.1.0"
)

app.include_router(health_router)
app.include_router(farmers_router)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
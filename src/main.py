"""Main application entry point."""
import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from src.controllers.controller import router as main_router
from src.controllers.onboarding_controller import router as onboarding_router
from src.db.session import init_db, seed_initial_data, tables_exist
from src.config.settings import settings

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


app = FastAPI(
    title="YieldSense API",
    description="Crop yield forecasting and farmer onboarding API service",
    version="0.1.0",
)

app.include_router(main_router)
app.include_router(onboarding_router)


@app.on_event("startup")
async def startup_event():
    """Initialize database and seed data on startup."""
    init_db()
    if settings.initialize_db:
        seed_initial_data()
    tables = tables_exist()
    assert tables["farmers"] and tables["crop_profiles"], "Database tables not initialized"
    print("✓ Database initialized and ready")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

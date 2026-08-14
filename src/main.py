"""Main application entry point."""
import sys
import uvicorn
from pathlib import Path
from fastapi import FastAPI
from src.config.settings import settings
from src.controllers.health_controller import router as health_router
from src.controllers.farmers_controller import router as farmers_router
from src.db.session import init_db, tables_exist, seed_initial_data

# Ensure the project root is on sys.path so the `src` package can be
# imported whether the process is started from the project root or
# from inside the `src/` directory (helps with `python -m uvicorn ...`).
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

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

@app.on_event("startup")
async def startup_event() -> None:
    """Application startup hook.

    Initialize database tables and verify expected tables are present. If
    the expected tables cannot be created or found, raise an exception so
    the process fails fast.
    """
    init_db()

    if settings.initialize_db:
        seed_initial_data()

    exists = tables_exist()
    missing = [name for name, ok in exists.items() if not ok]
    if missing:
        raise RuntimeError(f"Missing required tables after init: {missing}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

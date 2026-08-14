"""Main application entry point."""
import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from src.controllers.controller import router
from src.db.session import init_db, tables_exist, seed_initial_data

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if os.getenv("INITIALIZE_DB", "true").lower() == "true":
        seed_initial_data()
    missing = [name for name, ok in tables_exist().items() if not ok]
    if missing:
        raise RuntimeError(f"Missing required tables after init: {missing}")
    yield


app = FastAPI(
    title="YieldSense API",
    description="Crop yield forecasting and farmer onboarding API service",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

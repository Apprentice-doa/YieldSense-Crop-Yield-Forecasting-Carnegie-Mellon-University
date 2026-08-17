"""Main application entry point."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.controllers.controller import router as main_router
from src.controllers.onboarding_controller import router as onboarding_router
from src.controllers.auth_controller import router as auth_router
from src.controllers.chat_controller import router as chat_router
from src.db.session import init_db, seed_initial_data, tables_exist
from src.config.settings import settings

_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.initialize_db:
        seed_initial_data()
    tables = tables_exist()
    assert all(tables.values()), "Database tables not initialized"
    yield


app = FastAPI(
    title="YieldSense API",
    description="Crop yield forecasting and farmer onboarding API service",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(main_router)
app.include_router(onboarding_router)
app.include_router(auth_router)
app.include_router(chat_router)

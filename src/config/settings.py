"""Application settings for the YieldSense API.

This module centralizes runtime environment configuration and keeps the API
ready for containerized and local PostgreSQL-backed execution.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _parse_cors_origins() -> List[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    """Runtime application configuration."""

    app_name: str = os.getenv("APP_NAME", "YieldSense API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/YieldLensDb",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    initialize_db: bool = os.getenv("INITIALIZE_DB", "false").lower() == "true"
    # Development-only OTP used until a real email/SMS delivery provider is added.
    mock_otp: str = os.getenv("MOCK_OTP", "123456")
    cors_origins: List[str] = field(default_factory=_parse_cors_origins)


settings = Settings()

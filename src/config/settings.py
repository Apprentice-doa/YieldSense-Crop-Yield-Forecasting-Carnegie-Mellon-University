"""Application settings for the YieldSense API.

This module centralizes runtime environment configuration and keeps the API
ready for containerized and local PostgreSQL-backed execution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Runtime application configuration."""

    app_name: str = os.getenv("APP_NAME", "YieldSense API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://neondb_owner:npg_oyz7EbDVh1SG@ep-rapid-mode-ayv1ls40.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require",
    )
    redis_url: str = os.getenv(
        "REDIS_URL",
        "redis://default:6uOX0t85JhVmbqorB3tkVuHqJ7C5EkQE@tuned-ants-marble-22396.db.redis.io:12665",
    )
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    initialize_db: bool = os.getenv("INITIALIZE_DB", "false").lower() == "true"
    # Development-only OTP used until a real email/SMS delivery provider is added.
    mock_otp: str = os.getenv("MOCK_OTP", "123456")


settings = Settings()

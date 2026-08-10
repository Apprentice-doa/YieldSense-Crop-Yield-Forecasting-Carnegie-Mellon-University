"""Database session helpers for the API runtime."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.db.base import Base


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Initialize SQLAlchemy metadata for all DB models.

    The current scaffold does not yet register all domain models, but this hook
    keeps the API ready for the farmer and crop tables.
    """

    Base.metadata.create_all(bind=engine)

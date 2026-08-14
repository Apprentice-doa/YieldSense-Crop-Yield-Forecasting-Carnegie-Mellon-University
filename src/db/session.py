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
    # Import models so they are registered on the metadata
    # (these imports are local to avoid circular import during module import)
    try:
        from src.db.models.farmer import Farmer  # noqa: F401
        from src.db.models.crop_profile import CropProfile  # noqa: F401
    except Exception:
        # If models aren't available, create_all will be called anyway and
        # SQLAlchemy will ignore missing mappings. Keep the behavior
        # tolerant at init time.
        pass

    Base.metadata.create_all(bind=engine)


def tables_exist() -> dict:
    """Return a mapping of key table name to boolean existence in the DB."""

    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = {"farmers": inspector.has_table("farmers"), "crop_profiles": inspector.has_table("crop_profiles")}
    return tables

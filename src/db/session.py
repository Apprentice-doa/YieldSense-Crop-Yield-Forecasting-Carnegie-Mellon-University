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


def seed_initial_data(seed_path: str | None = None) -> None:
    """Seed the database with initial farmer and crop profile data.

    If tables already contain farmer records, the function is a no-op.
    The seed data is expected to be a JSON array of farmers with a
    `crop_profiles` list for each farmer.
    """

    import json
    from pathlib import Path

    # local import to avoid circular import issues at module import time
    from src.db.models.farmer import Farmer
    from src.db.models.crop_profile import CropProfile

    seed_file = Path(seed_path or "data/initial_data/farmers_seed.json")
    if not seed_file.exists():
        return

    # Use a session to check for existing data
    with SessionLocal() as session:
        existing = session.query(Farmer).first()
        if existing:
            return

        with open(seed_file, "r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except Exception:
                return

        for record in data:
            farmer = Farmer(
                name=record.get("name"),
                farm_country=record.get("farm_country"),
                farm_state_region=record.get("farm_state_region"),
                phone_number=record.get("phone_number"),
                email_address=record.get("email_address"),
                area_of_farmland=record.get("area_of_farmland") or 0.0,
            )
            session.add(farmer)
            session.flush()

            for cp in record.get("crop_profiles", []):
                crop = CropProfile(
                    farmer_id=farmer.id,
                    crop_type=cp.get("crop_type"),
                    planting_month=cp.get("planting_month"),
                    harvest_month=cp.get("harvest_month"),
                    average_yield_tons=cp.get("average_yield_tons") or 0.0,
                )
                session.add(crop)

        session.commit()

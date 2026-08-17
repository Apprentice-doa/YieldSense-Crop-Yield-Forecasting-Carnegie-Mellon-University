from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
import json
from pathlib import Path

from src.config.settings import settings
from src.db.base import Base

load_dotenv()

engine = create_engine(settings.database_url, future=True)
DBSession = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables in the database based on ORM models."""
    # Import every model before inspecting metadata.  This keeps table creation
    # reliable for scripts that import this module without importing a router.
    import src.db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def tables_exist():
    """Check which expected tables exist in the database."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    return {
        "farmers": "farmers" in existing_tables,
        "crop_profiles": "crop_profiles" in existing_tables,
        "conversations": "conversations" in existing_tables,
        "messages": "messages" in existing_tables,
    }


def seed_initial_data():
    """Seed the database with initial data if tables are empty."""
    from src.db.models.farmer import Farmer
    from src.db.models.crop_profile import CropProfile

    db = DBSession()
    try:
        # Check if farmers table is empty
        existing_farmers = db.query(Farmer).count()
        if existing_farmers > 0:
            print("Database already seeded, skipping seed_initial_data")
            return

        # Load seed data from JSON
        seed_file = Path(__file__).parent.parent.parent / "data" / "initial_data" / "farmers_seed.json"
        if not seed_file.exists():
            print(f"Seed file not found: {seed_file}")
            return

        with open(seed_file, "r") as f:
            seed_data = json.load(f)

        # Insert farmers and their crop profiles
        for farmer_data in seed_data:
            crop_profiles = farmer_data.pop("crop_profiles", [])
            farmer = Farmer(**farmer_data)
            db.add(farmer)
            db.flush()

            for cp_data in crop_profiles:
                cp = CropProfile(farmer_id=farmer.id, **cp_data)
                db.add(cp)

        db.commit()
        print(f"Seeded {len(seed_data)} farmers with crop profiles")
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


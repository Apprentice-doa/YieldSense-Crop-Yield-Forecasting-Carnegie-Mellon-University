from __future__ import annotations
from sqlalchemy.orm import Session
from typing import List
from src.repositories.farmer_repository import FarmerRepository
from src.db.models.farmer import Farmer
from src.db.models.crop_profile import CropProfile

class FarmerService:
    def __init__(self, db: Session):
        self.repo = FarmerRepository(db)
        self.db = db

    def create_farmer(self, payload: dict) -> Farmer:
        farmer = Farmer(
            name=payload.get("name"),
            farm_country=payload.get("farm_country"),
            farm_state_region=payload.get("farm_state_region"),
            phone_number=payload.get("phone_number"),
            email_address=payload.get("email_address"),
            area_of_farmland=payload.get("area_of_farmland") or 0.0,
        )
        self.repo.create(farmer)

        for cp in payload.get("crop_profiles", []):
            crop = CropProfile(
                farmer_id=farmer.id,
                crop_type=cp.get("crop_type"),
                planting_month=cp.get("planting_month"),
                harvest_month=cp.get("harvest_month"),
                average_yield_tons=cp.get("average_yield_tons") or 0.0,
            )
            self.db.add(crop)

        self.repo.commit()
        return farmer

    def list_farmers(self, limit: int = 100):
        return self.repo.list(limit=limit)

    def get_farmer(self, farmer_id: int):
        return self.repo.get_by_id(farmer_id)

    def delete_farmer(self, farmer_id: int):
        farmer = self.repo.get_by_id(farmer_id)
        if not farmer:
            return False
        self.repo.delete(farmer)
        self.repo.commit()
        return True

    def update_farmer(self, farmer_id: int, changes: dict) -> Farmer | None:
        farmer = self.repo.get_by_id(farmer_id)
        if not farmer:
            return None

        # Validation: unique phone and email
        phone = changes.get("phone_number")
        if phone:
            existing = self.repo.find_by_phone(phone)
            if existing and existing.id != farmer.id:
                raise ValueError("phone_exists")

        email = changes.get("email_address")
        if email:
            existing_e = self.repo.find_by_email(email)
            if existing_e and existing_e.id != farmer.id:
                raise ValueError("email_exists")

        # Handle crop_profiles replacement if provided
        crop_profiles = changes.pop("crop_profiles", None)

        # Apply simple field updates
        self.repo.update(farmer, changes)

        if crop_profiles is not None:
            # delete existing crop profiles and add new ones
            # eager-delete via query
            self.db.query(CropProfile).filter(CropProfile.farmer_id == farmer.id).delete()
            for cp in crop_profiles:
                new_cp = CropProfile(
                    farmer_id=farmer.id,
                    crop_type=cp.get("crop_type") if isinstance(cp, dict) else getattr(cp, "crop_type", None),
                    planting_month=cp.get("planting_month") if isinstance(cp, dict) else getattr(cp, "planting_month", None),
                    harvest_month=cp.get("harvest_month") if isinstance(cp, dict) else getattr(cp, "harvest_month", None),
                    average_yield_tons=cp.get("average_yield_tons") if isinstance(cp, dict) else getattr(cp, "average_yield_tons", 0.0),
                )
                self.db.add(new_cp)

        self.repo.commit()
        return farmer

from __future__ import annotations

from sqlalchemy.orm import Session
from typing import List, Optional

from src.db.models.farmer import Farmer
from src.db.models.crop_profile import CropProfile


class FarmerRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, farmer: Farmer) -> Farmer:
        self.db.add(farmer)
        self.db.flush()
        return farmer

    def get_by_id(self, farmer_id: int) -> Optional[Farmer]:
        return self.db.query(Farmer).filter(Farmer.id == farmer_id).first()

    def list(self, limit: int = 100) -> List[Farmer]:
        return self.db.query(Farmer).limit(limit).all()

    def delete(self, farmer: Farmer) -> None:
        self.db.delete(farmer)

    def commit(self) -> None:
        self.db.commit()

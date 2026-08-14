from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.db.base import Base

class CropProfile(Base):
    __tablename__ = "crop_profiles"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_type = Column(String, nullable=False)
    planting_month = Column(String, nullable=False)
    harvest_month = Column(String, nullable=False)
    average_yield_tons = Column(Float, default=0.0)

    farmer = relationship("Farmer", back_populates="crop_profiles")

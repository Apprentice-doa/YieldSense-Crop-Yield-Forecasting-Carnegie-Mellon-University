from __future__ import annotations

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from src.db.base import Base


class YieldRecord(Base):
    __tablename__ = "yield_records"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    crop_type = Column(String, nullable=False)
    season = Column(String, nullable=False)          # e.g. "Long Rains 2024"
    planting_date = Column(Date, nullable=True)
    harvest_date = Column(Date, nullable=True)
    predicted_yield_kg_per_ha = Column(Float, nullable=False)
    actual_yield_kg_per_ha = Column(Float, nullable=True)   # farmer reports back
    created_at = Column(Date, server_default=func.current_date())

    farmer = relationship("Farmer", back_populates="yield_records")

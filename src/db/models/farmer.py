from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Float, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship

from src.db.base import Base

class Farmer(Base):
    __tablename__ = "farmers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    farm_country = Column(String, nullable=False)
    farm_state_region = Column(String, nullable=False)
    phone_number = Column(String, unique=True, nullable=False)
    email_address = Column(String, unique=True, nullable=False)
    area_of_farmland = Column(Float, default=0.0)
    
    # Authentication fields
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    otp_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    crop_profiles = relationship("CropProfile", back_populates="farmer", cascade="all, delete-orphan")
    yield_records = relationship("YieldRecord", back_populates="farmer", cascade="all, delete-orphan")


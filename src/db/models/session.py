"""Session model for tracking active farmer sessions and tokens."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from src.db.base import Base


class FarmerSession(Base):
    """Tracks active sessions, tokens, and refresh tokens for farmers."""

    __tablename__ = "farmer_sessions"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    session_id = Column(String, unique=True, nullable=False, index=True)  # GUID
    
    # Token fields
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False, unique=True)
    token_type = Column(String, default="Bearer")
    
    # Expiry times
    access_token_expires_at = Column(DateTime, nullable=False)
    refresh_token_expires_at = Column(DateTime, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Metadata
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    farmer = relationship("Farmer", backref="sessions")

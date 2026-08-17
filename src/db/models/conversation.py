"""Conversation and Message models for farmer chats."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from src.db.base import Base


class SenderType(str, enum.Enum):
    """Type of message sender."""
    FARMER = "farmer"
    AI = "ai"
    SYSTEM = "system"
    ADVISOR = "advisor"


class MessageType(str, enum.Enum):
    """Type of message content."""
    TEXT = "text"
    SYSTEM = "system"
    ALERT = "alert"


class Conversation(Base):
    """Represents a chat conversation/thread between farmer and AI/advisor."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)

    # The UUID returned by the live chat API.  Keeping it separate from the
    # database primary key lets Redis sessions remain an implementation detail
    # while providing a stable public identifier for history retrieval.
    external_id = Column(String(36), unique=True, nullable=True, index=True)
    
    # Metadata
    title = Column(String, nullable=True)  # Optional title/topic
    description = Column(Text, nullable=True)
    
    # Context (for AI/recommendation context)
    context_type = Column(String, nullable=True)  # e.g., "yield_prediction", "weather_advisory", "general"
    context_data = Column(String, nullable=True)  # JSON string with context metadata
    
    # Status
    is_active = Column(String, default="active")  # active, archived, closed
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    farmer = relationship("Farmer", backref="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    """Individual message in a conversation."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)
    
    # Message details
    sender_type = Column(SQLEnum(SenderType), default=SenderType.FARMER, nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT, nullable=False)
    
    # Metadata (renamed from metadata to avoid SQLAlchemy conflict)
    context = Column(Text, nullable=True)  # JSON string for additional data
    is_read = Column(String, default="unread")  # unread, read
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    farmer = relationship("Farmer", backref="messages")

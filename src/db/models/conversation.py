"""Conversation and Message models for farmer chats."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from src.db.base import Base


class SenderType(str, enum.Enum):
    FARMER = "farmer"
    AI = "ai"


class Conversation(Base):
    """Represents a chat conversation/thread between farmer and AI/advisor."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False, index=True)

    # The UUID returned by the live chat API.  Keeping it separate from the
    # database primary key lets Redis sessions remain an implementation detail
    # while providing a stable public identifier for history retrieval.
    external_id = Column(String(36), unique=True, nullable=True, index=True)
    
    title = Column(String, nullable=True)
    context_type = Column(String, nullable=True)
    is_active = Column(String, default="active")  # active, archived
    
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
    
    sender_type = Column(SQLEnum(SenderType), default=SenderType.FARMER, nullable=False)
    content = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # JSON string for tool call metadata

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    farmer = relationship("Farmer", backref="messages")

"""Request and response schemas for chat functionality."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MessageCreateRequest(BaseModel):
    """Request to create a new message in a conversation."""

    content: str = Field(..., min_length=1)
    message_type: str = Field(default="text")


class MessageResponse(BaseModel):
    """Response for a message."""

    id: int
    conversation_id: int
    farmer_id: int
    sender_type: str
    content: str
    message_type: str
    is_read: str
    created_at: datetime

    class Config:
        orm_mode = True


class ConversationCreateRequest(BaseModel):
    """Request to create a new conversation."""

    title: Optional[str] = None
    description: Optional[str] = None
    context_type: Optional[str] = None  # e.g., "yield_prediction", "weather", "general"


class ConversationResponse(BaseModel):
    """Response for a conversation."""

    id: int
    external_id: Optional[str] = None
    farmer_id: int
    title: Optional[str]
    description: Optional[str]
    context_type: Optional[str]
    is_active: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None

    class Config:
        orm_mode = True


class ConversationDetailResponse(BaseModel):
    """Detailed conversation response with all messages."""

    id: int
    external_id: Optional[str] = None
    farmer_id: int
    title: Optional[str]
    description: Optional[str]
    context_type: Optional[str]
    is_active: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        orm_mode = True


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    content: str = Field(..., min_length=1, max_length=10000)
    message_type: str = Field(default="text")


class ChatSessionResponse(BaseModel):
    """Response containing recent messages for a conversation."""

    conversation_id: int
    messages: List[MessageResponse]
    total_unread: int

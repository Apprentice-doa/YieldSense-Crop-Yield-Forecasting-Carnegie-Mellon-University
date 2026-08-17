"""Request and response schemas for chat functionality."""

from __future__ import annotations

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    farmer_id: int
    sender_type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    external_id: Optional[str] = None
    farmer_id: int
    title: Optional[str]
    context_type: Optional[str]
    is_active: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: int
    external_id: Optional[str] = None
    farmer_id: int
    title: Optional[str]
    context_type: Optional[str]
    is_active: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True

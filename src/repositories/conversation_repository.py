"""Repository for managing conversations and messages."""

from __future__ import annotations

from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from src.db.models.conversation import Conversation, Message


class ConversationRepository:
    """Data access layer for conversations."""

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(self, conversation: Conversation) -> Conversation:
        """Create a new conversation."""
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_conversation_by_external_id(self, external_id: str) -> Optional[Conversation]:
        """Get a chat conversation using the UUID exposed by the chat API."""
        return (
            self.db.query(Conversation)
            .filter(Conversation.external_id == external_id)
            .first()
        )

    def get_farmer_conversations(self, farmer_id: int, is_active: str = "active") -> List[Conversation]:
        """Get all conversations for a farmer."""
        query = self.db.query(Conversation).filter(Conversation.farmer_id == farmer_id)
        if is_active:
            query = query.filter(Conversation.is_active == is_active)
        return query.order_by(Conversation.updated_at.desc()).all()

    def update_conversation(self, conversation: Conversation, updates: dict) -> Conversation:
        """Update conversation fields."""
        for key, value in updates.items():
            if hasattr(conversation, key) and key != "id":
                setattr(conversation, key, value)
        self.db.flush()
        return conversation

    def archive_conversation(self, conversation_id: int) -> bool:
        """Archive a conversation."""
        conv = self.get_conversation_by_id(conversation_id)
        if not conv:
            return False
        conv.is_active = "archived"
        self.db.flush()
        return True

    def delete_conversation(self, conversation: Conversation) -> None:
        """Delete a conversation and all its messages."""
        self.db.delete(conversation)

    def commit(self) -> None:
        """Commit transaction."""
        self.db.commit()


class MessageRepository:
    """Data access layer for messages."""

    def __init__(self, db: Session):
        self.db = db

    def create_message(self, message: Message) -> Message:
        """Create a new message."""
        self.db.add(message)
        self.db.flush()
        return message

    def get_message_by_id(self, message_id: int) -> Optional[Message]:
        """Get message by ID."""
        return self.db.query(Message).filter(Message.id == message_id).first()

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """Get messages for a conversation with pagination."""
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_unread_messages(self, conversation_id: int) -> List[Message]:
        """Get unread messages in a conversation."""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.is_read == "unread"
        ).all()

    def get_farmer_unread_count(self, farmer_id: int) -> int:
        """Count unread messages for a farmer across all conversations."""
        return self.db.query(Message).filter(
            Message.farmer_id == farmer_id,
            Message.is_read == "unread",
            Message.sender_type != "farmer",
        ).count()

    def mark_as_read(self, message_id: int) -> bool:
        """Mark a message as read."""
        msg = self.get_message_by_id(message_id)
        if not msg:
            return False
        msg.is_read = "read"
        self.db.flush()
        return True

    def mark_conversation_as_read(self, conversation_id: int) -> None:
        """Mark all messages in a conversation as read."""
        self.db.query(Message).filter(
            Message.conversation_id == conversation_id,
            Message.is_read == "unread"
        ).update({"is_read": "read"})
        self.db.flush()

    def delete_message(self, message: Message) -> None:
        """Delete a message."""
        self.db.delete(message)

    def commit(self) -> None:
        """Commit transaction."""
        self.db.commit()

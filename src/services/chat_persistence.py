"""Database chat persistence service for saving and retrieving conversations."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

from src.repositories.conversation_repository import ConversationRepository, MessageRepository
from src.db.models.conversation import Conversation, Message, SenderType, MessageType


class ChatPersistenceService:
    """Service for persisting chat conversations and messages to database.
    
    This layer saves AI chat conversations from Redis to PostgreSQL for
    long-term storage and retrieval.
    """

    def __init__(self, db: Session):
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)
        self.db = db

    def create_conversation(
        self,
        farmer_id: int,
        title: str = None,
        description: str = None,
        context_type: str = None,
        external_id: str = None,
    ) -> Conversation:
        """Create a new conversation for a farmer.
        
        Args:
            farmer_id: ID of farmer starting the conversation
            title: Optional conversation title
            description: Optional description
            context_type: Optional context (e.g., yield_prediction, weather_advisory)
            
        Returns:
            Created Conversation object
        """
        conversation = Conversation(
            farmer_id=farmer_id,
            title=title,
            description=description,
            context_type=context_type,
            external_id=external_id,
            is_active="active",
        )
        self.conv_repo.create_conversation(conversation)
        self.conv_repo.commit()
        return conversation

    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Get a conversation by ID."""
        if isinstance(conversation_id, int) or str(conversation_id).isdigit():
            conversation = self.conv_repo.get_conversation_by_id(int(conversation_id))
            if conversation:
                return conversation
        return self.conv_repo.get_conversation_by_external_id(str(conversation_id))

    def get_or_create_chat_conversation(
        self,
        farmer_id: int,
        external_id: str,
        title: str | None = None,
    ) -> Conversation:
        """Return the durable record for a live chat UUID, creating it once."""
        conversation = self.conv_repo.get_conversation_by_external_id(external_id)
        if conversation:
            if conversation.farmer_id != farmer_id:
                raise ValueError("conversation_not_found")
            return conversation
        return self.create_conversation(
            farmer_id=farmer_id,
            title=title,
            context_type="ai_chat",
            external_id=external_id,
        )

    def get_farmer_conversations(self, farmer_id: int, status: str = "active") -> List[Conversation]:
        """Get all conversations for a farmer."""
        return self.conv_repo.get_farmer_conversations(farmer_id, status)

    def archive_conversation(self, conversation_id: int) -> bool:
        """Archive a conversation."""
        result = self.conv_repo.archive_conversation(conversation_id)
        if result:
            self.conv_repo.commit()
        return result

    def save_message(
        self,
        conversation_id: int,
        farmer_id: int,
        content: str,
        sender_type: str = "farmer",
        message_type: str = "text",
        context: str = None,
    ) -> Message:
        """Save a message to the database.
        
        Args:
            conversation_id: ID of conversation
            farmer_id: ID of farmer (message owner)
            content: Message content
            sender_type: Type of sender (farmer, ai, advisor, system)
            message_type: Type of message (text, system, alert)
            context: Optional JSON context data
            
        Returns:
            Created Message object
        """
        # Validate conversation exists
        conv = self.get_conversation(conversation_id)
        if not conv:
            raise ValueError("conversation_not_found")
        if conv.farmer_id != farmer_id:
            # A message must always belong to the farmer who owns its thread.
            raise ValueError("conversation_not_found")

        # Create message
        message = Message(
            conversation_id=conv.id,
            farmer_id=farmer_id,
            sender_type=SenderType(sender_type) if isinstance(sender_type, str) else sender_type,
            content=content,
            message_type=MessageType(message_type) if isinstance(message_type, str) else message_type,
            is_read="unread" if SenderType(sender_type) != SenderType.FARMER else "read",
            context=context,
        )
        self.msg_repo.create_message(message)
        
        # Update conversation updated_at
        conv.updated_at = datetime.utcnow()
        self.db.flush()
        self.msg_repo.commit()
        
        return message

    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Message]:
        """Get messages from a conversation with pagination."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        return self.msg_repo.get_conversation_messages(conversation.id, limit, offset)

    def get_unread_messages(self, conversation_id: int) -> List[Message]:
        """Get unread messages in a conversation."""
        return self.msg_repo.get_unread_messages(conversation_id)

    def mark_message_as_read(self, message_id: int) -> bool:
        """Mark a message as read."""
        result = self.msg_repo.mark_as_read(message_id)
        if result:
            self.msg_repo.commit()
        return result

    def mark_conversation_as_read(self, conversation_id: int) -> None:
        """Mark all messages in a conversation as read."""
        self.msg_repo.mark_conversation_as_read(conversation_id)
        self.msg_repo.commit()

    def get_farmer_unread_count(self, farmer_id: int) -> int:
        """Get total unread message count for a farmer."""
        return self.msg_repo.get_farmer_unread_count(farmer_id)

    def get_conversation_summary(self, conversation_id: int) -> dict:
        """Get a summary of a conversation.
        
        Returns:
            Dictionary with conversation info and message count
        """
        conv = self.get_conversation(conversation_id)
        if not conv:
            return None

        msg_count = len(conv.messages)
        unread_count = len(self.msg_repo.get_unread_messages(conversation_id))

        return {
            "conversation_id": conv.id,
            "title": conv.title,
            "description": conv.description,
            "message_count": msg_count,
            "unread_count": unread_count,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
        }

    def persist_redis_chat_to_db(
        self,
        farmer_id: int,
        conversation_id: str,
        history: List[dict],
        title: str = None,
    ) -> Conversation:
        """Persist a chat history from Redis to the database.
        
        Args:
            farmer_id: Farmer ID
            conversation_id: Session conversation ID
            history: List of message dicts from Redis with format:
                    [{"role": "user|assistant", "content": "...", "message_id": "..."}, ...]
            title: Optional conversation title
            
        Returns:
            Conversation object with all messages persisted
        """
        # Create conversation
        conv = self.create_conversation(
            farmer_id=farmer_id,
            title=title or f"Conversation {conversation_id[:8]}",
            context_type="ai_chat",
        )

        # Save each message from history
        for msg_data in history:
            role = msg_data.get("role", "user")
            content = msg_data.get("content", "")
            
            # Determine sender type based on role
            sender_type = "ai" if role == "assistant" else "farmer"
            
            self.save_message(
                conversation_id=conv.id,
                farmer_id=farmer_id,
                content=content,
                sender_type=sender_type,
                message_type="text",
                context=None,
            )

        return conv

    def get_farmer_all_conversations(self, farmer_id: int) -> dict:
        """Get all conversations for a farmer including active and archived."""
        active = self.conv_repo.get_farmer_conversations(farmer_id, "active")
        archived = self.conv_repo.get_farmer_conversations(farmer_id, "archived")
        
        return {
            "active_conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "message_count": len(c.messages),
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in active
            ],
            "archived_conversations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "message_count": len(c.messages),
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in archived
            ],
        }

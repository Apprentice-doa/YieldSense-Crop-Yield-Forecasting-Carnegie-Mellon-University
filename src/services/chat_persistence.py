"""Database chat persistence service for saving and retrieving conversations."""

from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

from src.repositories.conversation_repository import ConversationRepository, MessageRepository
from src.db.models.conversation import Conversation, Message, SenderType


class ChatPersistenceService:

    def __init__(self, db: Session):
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)
        self.db = db

    def create_conversation(
        self,
        farmer_id: int,
        title: str = None,
        context_type: str = None,
        external_id: str = None,
    ) -> Conversation:
        conversation = Conversation(
            farmer_id=farmer_id,
            title=title,
            context_type=context_type,
            external_id=external_id,
            is_active="active",
        )
        self.conv_repo.create_conversation(conversation)
        self.conv_repo.commit()
        return conversation

    def get_conversation(self, conversation_id: int | str) -> Optional[Conversation]:
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
        return self.conv_repo.get_farmer_conversations(farmer_id, status)

    def archive_conversation(self, conversation_id: int) -> bool:
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
        context: str = None,
    ) -> Message:
        conv = self.get_conversation(conversation_id)
        if not conv or conv.farmer_id != farmer_id:
            raise ValueError("conversation_not_found")

        message = Message(
            conversation_id=conv.id,
            farmer_id=farmer_id,
            sender_type=SenderType(sender_type) if isinstance(sender_type, str) else sender_type,
            content=content,
            context=context,
        )
        self.msg_repo.create_message(message)
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
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        return self.msg_repo.get_conversation_messages(conversation.id, limit, offset)

    def get_message(self, message_id: int) -> Optional[Message]:
        return self.msg_repo.get_message_by_id(message_id)

    def mark_conversation_as_read(self, conversation_id: int) -> None:
        self.msg_repo.mark_conversation_as_read(conversation_id)
        self.msg_repo.commit()

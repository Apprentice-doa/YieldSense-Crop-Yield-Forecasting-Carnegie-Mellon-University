"""Chat controller for managing conversations and messages."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.chat_persistence import ChatPersistenceService
from src.schemas.chat_schema import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationDetailResponse,
    MessageCreateRequest,
    MessageResponse,
    SendMessageRequest,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationCreateRequest,
    farmer_id: int,
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Create a new conversation.
    
    - Each conversation is a thread of related messages
    - Can be titled and have optional context (yield_prediction, weather, etc)
    """
    svc = ChatPersistenceService(db)
    conv = svc.create_conversation(
        farmer_id=farmer_id,
        title=payload.title,
        description=payload.description,
        context_type=payload.context_type,
    )
    
    return ConversationResponse(
        id=conv.id,
        external_id=conv.external_id,
        farmer_id=conv.farmer_id,
        title=conv.title,
        description=conv.description,
        context_type=conv.context_type,
        is_active=conv.is_active,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=0,
    )


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_farmer_conversations(
    farmer_id: int,
    status: str = "active",
    db: Session = Depends(get_db),
) -> list[ConversationResponse]:
    """Get all conversations for a farmer.
    
    - Filter by status: active, archived, or all
    - Returns conversations ordered by most recent first
    """
    svc = ChatPersistenceService(db)
    conversations = svc.get_farmer_conversations(farmer_id, status if status != "all" else None)
    
    return [
        ConversationResponse(
            id=c.id,
            external_id=c.external_id,
            farmer_id=c.farmer_id,
            title=c.title,
            description=c.description,
            context_type=c.context_type,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
            message_count=len(c.messages),
        )
        for c in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """Get a specific conversation with all its messages.
    
    - Returns full conversation history
    - Messages ordered chronologically (oldest first)
    """
    svc = ChatPersistenceService(db)
    conv = svc.get_conversation(conversation_id)
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = svc.get_conversation_messages(conversation_id, limit=1000)
    
    return ConversationDetailResponse(
        id=conv.id,
        external_id=conv.external_id,
        farmer_id=conv.farmer_id,
        title=conv.title,
        description=conv.description,
        context_type=conv.context_type,
        is_active=conv.is_active,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                farmer_id=m.farmer_id,
                sender_type=m.sender_type.value,
                content=m.content,
                message_type=m.message_type.value,
                is_read=m.is_read,
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def send_message(
    conversation_id: int,
    payload: SendMessageRequest,
    farmer_id: int,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send a message in a conversation.
    
    - Farmer sends a message (sender_type = farmer)
    - Can integrate with AI service to generate AI response
    """
    svc = ChatPersistenceService(db)
    
    try:
        message = svc.save_message(
            conversation_id=conversation_id,
            farmer_id=farmer_id,
            content=payload.content,
            sender_type="farmer",
            message_type=payload.message_type,
        )
    except ValueError as e:
        if "conversation_not_found" in str(e):
            raise HTTPException(status_code=404, detail="Conversation not found")
        raise
    
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        farmer_id=message.farmer_id,
        sender_type=message.sender_type.value,
        content=message.content,
        message_type=message.message_type.value,
        is_read=message.is_read,
        created_at=message.created_at,
    )


@router.post("/conversations/{conversation_id}/messages/{message_id}/read")
async def mark_message_read(
    conversation_id: int,
    message_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Mark a message as read."""
    svc = ChatPersistenceService(db)
    ok = svc.mark_message_as_read(message_id)
    
    if not ok:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"status": "success", "message_id": message_id}


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Mark all messages in a conversation as read."""
    svc = ChatPersistenceService(db)
    svc.mark_conversation_as_read(conversation_id)
    
    return {"status": "success", "conversation_id": conversation_id}


@router.get("/conversations/{conversation_id}/unread")
async def get_unread_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get unread messages in a conversation."""
    svc = ChatPersistenceService(db)
    unread = svc.get_unread_messages(conversation_id)
    
    return {
        "conversation_id": conversation_id,
        "unread_count": len(unread),
        "messages": [
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                farmer_id=m.farmer_id,
                sender_type=m.sender_type.value,
                content=m.content,
                message_type=m.message_type.value,
                is_read=m.is_read,
                created_at=m.created_at,
            )
            for m in unread
        ],
    }


@router.get("/unread-count")
async def get_unread_count(
    farmer_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get total unread message count for a farmer."""
    svc = ChatPersistenceService(db)
    count = svc.get_farmer_unread_count(farmer_id)
    
    return {"farmer_id": farmer_id, "unread_count": count}


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Archive a conversation."""
    svc = ChatPersistenceService(db)
    ok = svc.archive_conversation(conversation_id)
    
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"status": "success", "conversation_id": conversation_id, "is_active": "archived"}


@router.get("/conversations/{conversation_id}/summary")
async def get_conversation_summary(
    conversation_id: int,
    db: Session = Depends(get_db),
) -> dict:
    """Get a summary of a conversation."""
    svc = ChatPersistenceService(db)
    summary = svc.get_conversation_summary(conversation_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return summary

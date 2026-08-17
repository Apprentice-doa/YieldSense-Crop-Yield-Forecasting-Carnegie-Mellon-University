"""Chat controller for conversation history and management."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.chat_persistence import ChatPersistenceService
from src.services.chat_service import chat, new_conversation
from src.utils.security import AuthenticatedFarmer, get_current_farmer, require_farmer_access
from src.schemas.chat_schema import (
    ConversationResponse,
    ConversationDetailResponse,
    MessageResponse,
)
from models.request import ChatRequest
from models.response import ChatResponse

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(get_current_farmer)],
)


def _owned_conversation(
    svc: ChatPersistenceService,
    conversation_id: str | int,
    current: AuthenticatedFarmer,
):
    conversation = svc.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    require_farmer_access(conversation.farmer_id, current)
    return conversation


@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> ChatResponse:
    """Send a message and get an AI reply."""
    require_farmer_access(payload.farmer_id, current)
    if payload.session_id != current.session_id:
        raise HTTPException(status_code=403, detail="The chat session does not belong to this token")
    return chat(
        session_id=payload.session_id,
        farmer_id=payload.farmer_id,
        user_message=payload.message,
        db=db,
        conversation_id=payload.conversation_id,
    )


@router.post("/new-conversation")
async def new_conversation_endpoint(
    session_id: str,
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> dict:
    """Start a fresh conversation within an existing session."""
    if session_id != current.session_id:
        raise HTTPException(status_code=403, detail="The chat session does not belong to this token")
    try:
        return {"conversation_id": new_conversation(session_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_farmer_conversations(
    farmer_id: int,
    status: str = "active",
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> list[ConversationResponse]:
    """Get all conversations for a farmer.
    
    - Filter by status: active, archived, or all
    - Returns conversations ordered by most recent first
    """
    require_farmer_access(farmer_id, current)
    svc = ChatPersistenceService(db)
    conversations = svc.get_farmer_conversations(farmer_id, status if status != "all" else None)
    
    return [
        ConversationResponse(
            id=c.id,
            external_id=c.external_id,
            farmer_id=c.farmer_id,
            title=c.title,
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
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> ConversationDetailResponse:
    """Get a specific conversation with all its messages.
    
    - Returns full conversation history
    - Messages ordered chronologically (oldest first)
    """
    svc = ChatPersistenceService(db)
    conv = _owned_conversation(svc, conversation_id, current)
    
    messages = svc.get_conversation_messages(conversation_id, limit=1000)
    
    return ConversationDetailResponse(
        id=conv.id,
        external_id=conv.external_id,
        farmer_id=conv.farmer_id,
        title=conv.title,
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
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.post("/conversations/{conversation_id}/read")
async def mark_conversation_read(
    conversation_id: int,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> dict:
    """Mark all messages in a conversation as read."""
    svc = ChatPersistenceService(db)
    _owned_conversation(svc, conversation_id, current)
    svc.mark_conversation_as_read(conversation_id)
    
    return {"status": "success", "conversation_id": conversation_id}


@router.post("/conversations/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current: AuthenticatedFarmer = Depends(get_current_farmer),
) -> dict:
    """Archive a conversation."""
    svc = ChatPersistenceService(db)
    _owned_conversation(svc, conversation_id, current)
    ok = svc.archive_conversation(conversation_id)
    
    if not ok:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"status": "success", "conversation_id": conversation_id, "is_active": "archived"}



"""Conversation routes — list, create, and read AI chat threads.

Endpoints (under /api/v1):
- GET  /conversations            list the user's conversations (recent first)
- POST /conversations            create an empty conversation
- GET  /conversations/{id}       a conversation with its full message history

All endpoints are scoped to the current (single) user.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_conversation_service, get_current_user_id
from backend.schemas.ai import (
    ConversationCreate,
    ConversationDetail,
    ConversationRead,
)
from backend.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    service: ConversationService = Depends(get_conversation_service),
) -> list[ConversationRead]:
    return service.list(user_id, limit=limit, offset=offset)


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(
    payload: ConversationCreate,
    user_id: int = Depends(get_current_user_id),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationRead:
    return service.create(user_id, title=payload.title)


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: int,
    user_id: int = Depends(get_current_user_id),
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetail:
    conversation = service.get(user_id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

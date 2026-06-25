"""AI routes — chat with the assistant plus diagnostics.

Endpoints (under /api/v1):
- POST /ai/chat         send a message, get the assistant reply (persisted)
- POST /ai/chat/stream  stream the reply + tool calls as Server-Sent Events
- GET  /ai/health       active provider, configured model, availability

Routes are thin: they depend on AIService and translate provider failures into
HTTP errors. Providers are never touched here.
"""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.dependencies import get_ai_service, get_current_user_id
from backend.integrations.ai.base import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)
from backend.schemas.ai import AIHealth, ChatRequest, ChatResult
from backend.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResult)
def chat(
    payload: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    service: AIService = Depends(get_ai_service),
) -> ChatResult:
    try:
        result = service.chat(
            user_id,
            message=payload.message,
            conversation_id=payload.conversation_id,
            system_prompt_id=payload.system_prompt_id,
        )
    except ProviderAuthError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ProviderError as exc:  # any other provider failure
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if result is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    user_id: int = Depends(get_current_user_id),
    service: AIService = Depends(get_ai_service),
) -> StreamingResponse:
    """Stream the assistant reply as Server-Sent Events.

    The service emits typed events (conversation/tool_call/token/done/error);
    provider failures arrive as an ``error`` event rather than an HTTP status,
    since the response has already begun streaming.
    """

    def event_stream():
        for event in service.stream(
            user_id,
            message=payload.message,
            conversation_id=payload.conversation_id,
            system_prompt_id=payload.system_prompt_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health", response_model=AIHealth)
def ai_health(
    service: AIService = Depends(get_ai_service),
) -> AIHealth:
    return service.health()

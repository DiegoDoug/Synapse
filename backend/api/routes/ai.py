"""AI routes — chat with the assistant plus diagnostics.

Endpoints (under /api/v1):
- POST /ai/chat       send a message, get the assistant reply (persisted)
- GET  /ai/health     active provider, configured model, availability

Routes are thin: they depend on AIService and translate provider failures into
HTTP errors. Providers are never touched here.
"""

from fastapi import APIRouter, Depends, HTTPException

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


@router.get("/health", response_model=AIHealth)
def ai_health(
    service: AIService = Depends(get_ai_service),
) -> AIHealth:
    return service.health()

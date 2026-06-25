"""Prompt routes — selectable system prompts for the assistant.

Endpoints (under /api/v1):
- GET /prompts        list the available system prompts

Read-only in this stage; prompt authoring/management is a later concern.
"""

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_ai_service
from backend.schemas.ai import SystemPromptRead
from backend.services.ai_service import AIService

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[SystemPromptRead])
def list_prompts(
    service: AIService = Depends(get_ai_service),
) -> list[SystemPromptRead]:
    return service.list_prompts()

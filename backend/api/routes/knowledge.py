"""Knowledge routes — semantic search over the personal knowledge base.

Endpoints (under /api/v1):
- GET /knowledge/search   semantic search over indexed document chunks

Scoped to the current (single) user. The same retrieval also backs the
``search_knowledge`` tool the assistant uses to ground its answers; this endpoint
exposes it directly for the knowledge-search UI.
"""

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_current_user_id, get_knowledge_service
from backend.schemas.document import KnowledgeSearchResponse
from backend.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    query: str = Query(..., min_length=1, description="Semantic search query."),
    limit: int = Query(5, ge=1, le=20),
    user_id: int = Depends(get_current_user_id),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeSearchResponse:
    return service.search_response(user_id, query, limit=limit)

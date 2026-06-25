"""Document request/response schemas (DTOs) for the knowledge base."""

from datetime import datetime

from pydantic import BaseModel


class DocumentRead(BaseModel):
    """Read-view of a knowledge-base document and its index status."""

    id: int
    filename: str
    content_type: str | None = None
    size_bytes: int = 0
    status: str
    error: str | None = None
    char_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None = None


class KnowledgeStatus(BaseModel):
    """Capabilities of the knowledge subsystem (for the documents UI)."""

    embeddings_available: bool
    embedding_model: str
    vector_backend: str


class KnowledgeHit(BaseModel):
    """A single semantic-search match: an excerpt and its source document."""

    document_id: int
    filename: str
    chunk_index: int
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    """Result of a semantic search over the knowledge base."""

    query: str
    available: bool  # whether semantic search is online (embeddings installed)
    hits: list[KnowledgeHit] = []

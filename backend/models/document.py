"""Document + DocumentChunk models (SQLModel). Schema only — no business logic.

A ``Document`` is a file the user uploaded into their personal knowledge base.
``DocumentService`` extracts its text, splits it into ``DocumentChunk`` rows, and
embeds each chunk for retrieval (RAG). The chunk's embedding vector is persisted
here as JSON so the in-process vector store can be rebuilt without re-embedding,
and so chunk text is always available for citations regardless of the vector
backend.

Status lifecycle (owned by the service):
``pending`` → ``indexing`` → ``indexed`` | ``failed`` | ``unavailable``
(``unavailable`` means text was extracted but embeddings were not installed, so
the document can be re-indexed later without re-uploading).
"""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Document(SQLModel, table=True):
    """A persisted knowledge-base document and its index status."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    filename: str
    content_type: str | None = Field(default=None)
    size_bytes: int = Field(default=0)

    # Index lifecycle — drives the status badge in the documents UI.
    status: str = Field(default="pending", index=True)
    error: str | None = Field(default=None)

    char_count: int = Field(default=0)
    chunk_count: int = Field(default=0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), index=True
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    indexed_at: datetime | None = Field(default=None)


class DocumentChunk(SQLModel, table=True):
    """A single embedded text chunk belonging to a Document."""

    id: int | None = Field(default=None, primary_key=True)
    document_id: int = Field(foreign_key="document.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    chunk_index: int = Field(default=0)
    content: str
    char_count: int = Field(default=0)

    # JSON-encoded list[float]; null until embeddings are available. Stored so the
    # in-process vector index survives a restart without re-embedding.
    embedding: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

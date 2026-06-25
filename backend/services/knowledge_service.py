"""KnowledgeService — semantic search over indexed document chunks (RAG read).

Embeds the query, asks the vector store for the closest chunks belonging to the
user, and resolves them back to their text + source document for citations. It is
the read side of the knowledge base; ``DocumentService`` (ingestion) produces the
index it searches.

When the in-process fallback store is used, the index lives only in memory and is
empty after a restart while documents persist in the database. ``search`` lazily
re-seeds it from the embeddings stored on ``DocumentChunk`` rows, so the fallback
is durable without re-embedding. External stores (Qdrant) own their persistence,
so re-seeding is a no-op for them.

Graceful degradation: with embeddings uninstalled, ``available()`` is False and
``search`` returns no hits instead of raising.
"""

from __future__ import annotations

import json
import logging

from backend.integrations.embeddings.base import EmbeddingModel
from backend.integrations.vectorstore.base import VectorRecord, VectorStore
from backend.integrations.vectorstore.memory_store import InProcessVectorStore
from backend.repositories.document_repository import DocumentRepository
from backend.schemas.document import KnowledgeHit, KnowledgeSearchResponse

logger = logging.getLogger(__name__)

_MAX_LIMIT = 20


class KnowledgeService:
    """Semantic search over the user's indexed knowledge-base chunks."""

    def __init__(
        self,
        documents: DocumentRepository,
        embeddings: EmbeddingModel,
        vectors: VectorStore,
    ) -> None:
        self._documents = documents
        self._embeddings = embeddings
        self._vectors = vectors

    def available(self) -> bool:
        """Whether semantic search can run (the embedding model is installed)."""
        return self._embeddings.available()

    def search(
        self, user_id: int, query: str, *, limit: int = 5
    ) -> list[KnowledgeHit]:
        """Return the chunks most relevant to ``query``, best first (may be empty)."""
        query = (query or "").strip()
        limit = max(1, min(limit, _MAX_LIMIT))
        if not query or not self._embeddings.available():
            return []

        self._ensure_index(user_id)
        try:
            vector = self._embeddings.encode([query])[0]
        except Exception as exc:  # noqa: BLE001 — degrade instead of failing search
            logger.warning("Query embedding failed: %s", exc)
            return []

        matches = self._vectors.search(vector, user_id=user_id, limit=limit)
        if not matches:
            return []

        chunks = {c.id: c for c in self._documents.get_chunks([m.id for m in matches])}
        doc_cache: dict[int, str] = {}
        hits: list[KnowledgeHit] = []
        for match in matches:
            chunk = chunks.get(match.id)
            if chunk is None:
                continue
            filename = doc_cache.get(chunk.document_id)
            if filename is None:
                document = self._documents.get(chunk.document_id)
                filename = document.filename if document else "unknown"
                doc_cache[chunk.document_id] = filename
            hits.append(
                KnowledgeHit(
                    document_id=chunk.document_id,
                    filename=filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=round(float(match.score), 4),
                )
            )
        return hits

    def search_response(
        self, user_id: int, query: str, *, limit: int = 5
    ) -> KnowledgeSearchResponse:
        """Search wrapped with availability, for the REST endpoint."""
        return KnowledgeSearchResponse(
            query=query,
            available=self.available(),
            hits=self.search(user_id, query, limit=limit),
        )

    # --- Internals --------------------------------------------------------

    def _ensure_index(self, user_id: int) -> None:
        """Re-seed the in-process index from persisted embeddings when empty.

        No-op for external vector stores (they own their persistence).
        """
        store = self._vectors
        if not isinstance(store, InProcessVectorStore) or store.has_user(user_id):
            return
        records = [
            VectorRecord(
                id=chunk.id,
                vector=json.loads(chunk.embedding),
                payload={
                    "user_id": chunk.user_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for chunk in self._documents.list_embedded_chunks(user_id)
            if chunk.embedding
        ]
        if records:
            store.upsert(records)

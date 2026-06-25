"""DocumentService — knowledge-base ingestion and management.

Owns the ingestion pipeline: extract text → chunk → embed → index, plus listing
and deletion. It talks to the embeddings and vector-store integrations through
the integration seam (never importing their heavy libs directly) and persists
documents + chunks via ``DocumentRepository``. Search lives in
``KnowledgeService`` (Major Feature 2); this service produces the index it reads.

Graceful degradation: when embeddings are unavailable the document is still
stored with its extracted text and chunks but marked ``unavailable`` so it can be
re-indexed later without re-uploading. Any extraction/encoding failure is
recorded on the document as ``failed`` rather than raising to the caller.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from backend.integrations.embeddings.base import (
    EmbeddingModel,
    EmbeddingUnavailableError,
)
from backend.integrations.vectorstore.base import VectorRecord, VectorStore
from backend.integrations.vectorstore.memory_store import InProcessVectorStore
from backend.models.document import Document, DocumentChunk
from backend.repositories.document_repository import DocumentRepository
from backend.schemas.document import DocumentRead, KnowledgeStatus
from backend.services.text_processing import ExtractionError, chunk_text, extract_text

logger = logging.getLogger(__name__)


class DocumentService:
    """Ingest, list, and delete personal knowledge-base documents."""

    def __init__(
        self,
        documents: DocumentRepository,
        embeddings: EmbeddingModel,
        vectors: VectorStore,
        *,
        embedding_model_name: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        self._documents = documents
        self._embeddings = embeddings
        self._vectors = vectors
        self._embedding_model_name = embedding_model_name
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    # --- Status -----------------------------------------------------------

    def status(self) -> KnowledgeStatus:
        return KnowledgeStatus(
            embeddings_available=self._embeddings.available(),
            embedding_model=self._embedding_model_name,
            vector_backend=self._vectors.backend,
        )

    # --- Queries ----------------------------------------------------------

    def list(self, user_id: int) -> list[DocumentRead]:
        return [self._read(d) for d in self._documents.list_for_user(user_id)]

    def get(self, user_id: int, document_id: int) -> DocumentRead | None:
        document = self._documents.get_for_user(user_id, document_id)
        return self._read(document) if document else None

    def delete(self, user_id: int, document_id: int) -> bool:
        document = self._documents.get_for_user(user_id, document_id)
        if document is None:
            return False
        self._vectors.delete_document(document.id)
        self._documents.delete(document)
        return True

    # --- Ingestion --------------------------------------------------------

    def ingest(
        self,
        user_id: int,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> DocumentRead:
        """Extract, chunk, embed, and index an uploaded file.

        Always returns a persisted document; its ``status`` reflects the outcome
        (``indexed`` / ``unavailable`` / ``failed``).
        """
        document = self._documents.add(
            Document(
                user_id=user_id,
                filename=filename,
                content_type=content_type,
                size_bytes=len(data),
                status="indexing",
            )
        )

        try:
            text = extract_text(filename, content_type, data)
        except ExtractionError as exc:
            return self._fail(document, str(exc))

        text = text.strip()
        document.char_count = len(text)
        if not text:
            return self._fail(document, "No extractable text found in the file.")

        chunks = chunk_text(
            text, chunk_size=self._chunk_size, overlap=self._chunk_overlap
        )

        if not self._embeddings.available():
            # Persist chunks without vectors so the document can be re-indexed
            # once embeddings are installed, without re-uploading.
            self._persist_chunks(user_id, document.id, chunks, vectors=None)
            return self._finish(document, len(chunks), status="unavailable")

        try:
            vectors = self._embeddings.encode(chunks)
        except EmbeddingUnavailableError as exc:
            self._persist_chunks(user_id, document.id, chunks, vectors=None)
            return self._finish(
                document, len(chunks), status="unavailable", error=str(exc)
            )
        except Exception as exc:  # noqa: BLE001 — surface any encode failure
            logger.warning("Embedding failed for document %s: %s", document.id, exc)
            return self._fail(document, f"Embedding failed: {exc}")

        rows = self._persist_chunks(user_id, document.id, chunks, vectors=vectors)
        self._vectors.upsert(
            [
                VectorRecord(
                    id=row.id,
                    vector=vec,
                    payload={
                        "user_id": user_id,
                        "document_id": document.id,
                        "chunk_index": row.chunk_index,
                    },
                )
                for row, vec in zip(rows, vectors, strict=False)
            ]
        )
        return self._finish(document, len(chunks), status="indexed")

    # --- Internals --------------------------------------------------------

    def _persist_chunks(
        self,
        user_id: int,
        document_id: int,
        chunks: list[str],
        *,
        vectors: list[list[float]] | None,
    ) -> list[DocumentChunk]:
        rows = [
            DocumentChunk(
                document_id=document_id,
                user_id=user_id,
                chunk_index=index,
                content=content,
                char_count=len(content),
                embedding=(
                    json.dumps(vectors[index]) if vectors is not None else None
                ),
            )
            for index, content in enumerate(chunks)
        ]
        return self._documents.add_chunks(rows)

    def _finish(
        self,
        document: Document,
        chunk_count: int,
        *,
        status: str,
        error: str | None = None,
    ) -> DocumentRead:
        document.chunk_count = chunk_count
        document.status = status
        document.error = error
        document.indexed_at = datetime.now(UTC) if status == "indexed" else None
        return self._read(self._documents.update(document))

    def _fail(self, document: Document, error: str) -> DocumentRead:
        document.status = "failed"
        document.error = error
        return self._read(self._documents.update(document))

    @staticmethod
    def _read(document: Document) -> DocumentRead:
        return DocumentRead(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            status=document.status,
            error=document.error,
            char_count=document.char_count,
            chunk_count=document.chunk_count,
            created_at=document.created_at,
            updated_at=document.updated_at,
            indexed_at=document.indexed_at,
        )

    # --- Fallback re-seeding (used by KnowledgeService, MF2) --------------

    def reseed_memory_index(self, user_id: int) -> int:
        """Rebuild the in-process vector index from persisted chunk embeddings.

        No-op for external stores (e.g. Qdrant). Returns the number of vectors
        loaded. Lets the zero-dependency fallback survive a process restart.
        """
        store = self._vectors
        if not isinstance(store, InProcessVectorStore) or store.has_user(user_id):
            return 0
        records: list[VectorRecord] = []
        for chunk in self._documents.list_embedded_chunks(user_id):
            if not chunk.embedding:
                continue
            records.append(
                VectorRecord(
                    id=chunk.id,
                    vector=json.loads(chunk.embedding),
                    payload={
                        "user_id": chunk.user_id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                    },
                )
            )
        store.upsert(records)
        return len(records)

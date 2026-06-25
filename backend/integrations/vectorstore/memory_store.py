"""In-process vector store — the zero-dependency development fallback.

Keeps chunk vectors in a process-local dict and scores them with brute-force
cosine similarity. Vectors come back normalized from the embedding model, so the
dot product is the cosine. This needs no Qdrant server; for durability the
service re-seeds it from the embeddings persisted on ``DocumentChunk`` rows after
a restart, so the index is never silently empty while documents exist.
"""

from __future__ import annotations

import math

from backend.integrations.vectorstore.base import (
    VectorMatch,
    VectorRecord,
    VectorStore,
)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class InProcessVectorStore(VectorStore):
    """Brute-force in-memory cosine search over chunk vectors."""

    backend = "memory"

    def __init__(self) -> None:
        # chunk_id -> (vector, payload)
        self._records: dict[int, tuple[list[float], dict]] = {}

    def available(self) -> bool:
        return True

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            self._records[record.id] = (record.vector, dict(record.payload))

    def search(
        self, vector: list[float], *, user_id: int, limit: int = 5
    ) -> list[VectorMatch]:
        scored = [
            VectorMatch(id=chunk_id, score=_cosine(vector, stored), payload=payload)
            for chunk_id, (stored, payload) in self._records.items()
            if payload.get("user_id") == user_id
        ]
        scored.sort(key=lambda match: match.score, reverse=True)
        return scored[:limit]

    def delete_document(self, document_id: int) -> None:
        self._records = {
            chunk_id: value
            for chunk_id, value in self._records.items()
            if value[1].get("document_id") != document_id
        }

    # --- Fallback-only helpers -------------------------------------------

    def __len__(self) -> int:
        return len(self._records)

    def has_user(self, user_id: int) -> bool:
        return any(
            payload.get("user_id") == user_id
            for _, payload in self._records.values()
        )

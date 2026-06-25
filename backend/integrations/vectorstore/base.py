"""Vector store contract + shared value objects.

A ``VectorStore`` is a thin integration: it upserts chunk vectors keyed by chunk
id, searches by cosine similarity scoped to a user, and deletes a document's
points. Two implementations back it — an in-process fallback (no server needed)
and a Qdrant client — selected by configuration. Business logic (chunking,
embedding, citations) lives in the service layer, never here.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VectorRecord:
    """A single chunk vector to upsert, with its routing payload."""

    id: int
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorMatch:
    """A search hit: the chunk id, its similarity score, and its payload."""

    id: int
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class VectorStore(ABC):
    """Upsert + search dense vectors for the knowledge base."""

    #: Stable identifier for the active backend (surfaced to the UI).
    backend: str = "base"

    @abstractmethod
    def available(self) -> bool:
        """Whether the store is ready to serve upserts/searches."""
        raise NotImplementedError

    @abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self, vector: list[float], *, user_id: int, limit: int = 5
    ) -> list[VectorMatch]:
        """Return the closest chunks belonging to ``user_id``, best first."""
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, document_id: int) -> None:
        """Remove every point belonging to a document."""
        raise NotImplementedError

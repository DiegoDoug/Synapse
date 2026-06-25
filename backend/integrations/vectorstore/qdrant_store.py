"""Qdrant vector store (lazy client).

Wraps ``qdrant_client`` for production-grade vector search. The client is
imported lazily and the collection is created on first use, so importing this
module never requires Qdrant to be installed or reachable. When the client
library is absent or the server is unreachable, ``available()`` returns False and
the factory falls back to the in-process store.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.integrations.vectorstore.base import (
    VectorMatch,
    VectorRecord,
    VectorStore,
)

logger = logging.getLogger(__name__)


class QdrantVectorStore(VectorStore):
    """Upsert + search chunk vectors in a Qdrant collection."""

    backend = "qdrant"

    def __init__(self, url: str, collection: str, dimension: int) -> None:
        self._url = url
        self._collection = collection
        self._dimension = dimension
        self._client: Any | None = None
        self._ensured = False

    def _connect(self) -> Any | None:
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient
        except Exception:  # noqa: BLE001 — library not installed
            return None
        try:
            self._client = QdrantClient(url=self._url)
        except Exception as exc:  # noqa: BLE001 — bad URL / unreachable
            logger.warning("Qdrant unavailable at %s: %s", self._url, exc)
            return None
        return self._client

    def available(self) -> bool:
        client = self._connect()
        if client is None:
            return False
        try:
            client.get_collections()
        except Exception as exc:  # noqa: BLE001 — server unreachable
            logger.warning("Qdrant not reachable: %s", exc)
            return False
        return True

    def _ensure_collection(self, client: Any) -> None:
        if self._ensured:
            return
        from qdrant_client.models import Distance, VectorParams

        existing = {c.name for c in client.get_collections().collections}
        if self._collection not in existing:
            client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dimension, distance=Distance.COSINE
                ),
            )
        self._ensured = True

    def upsert(self, records: list[VectorRecord]) -> None:
        client = self._connect()
        if client is None or not records:
            return
        from qdrant_client.models import PointStruct

        self._ensure_collection(client)
        client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(id=r.id, vector=r.vector, payload=r.payload)
                for r in records
            ],
        )

    def search(
        self, vector: list[float], *, user_id: int, limit: int = 5
    ) -> list[VectorMatch]:
        client = self._connect()
        if client is None:
            return []
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            MatchValue,
        )

        self._ensure_collection(client)
        hits = client.search(
            collection_name=self._collection,
            query_vector=vector,
            limit=limit,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id", match=MatchValue(value=user_id)
                    )
                ]
            ),
        )
        return [
            VectorMatch(id=int(hit.id), score=float(hit.score), payload=hit.payload or {})
            for hit in hits
        ]

    def delete_document(self, document_id: int) -> None:
        client = self._connect()
        if client is None:
            return
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            FilterSelector,
            MatchValue,
        )

        self._ensure_collection(client)
        client.delete(
            collection_name=self._collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

"""Vector store integration — upsert + search chunk embeddings for RAG."""

from backend.integrations.vectorstore.base import (
    VectorMatch,
    VectorRecord,
    VectorStore,
)
from backend.integrations.vectorstore.memory_store import InProcessVectorStore
from backend.integrations.vectorstore.qdrant_store import QdrantVectorStore

__all__ = [
    "InProcessVectorStore",
    "QdrantVectorStore",
    "VectorMatch",
    "VectorRecord",
    "VectorStore",
]

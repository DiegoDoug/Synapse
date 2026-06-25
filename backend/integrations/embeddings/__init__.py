"""Embeddings integration — text → vector encoders for the knowledge base."""

from backend.integrations.embeddings.base import (
    EmbeddingModel,
    EmbeddingUnavailableError,
)
from backend.integrations.embeddings.sentence_transformer import (
    SentenceTransformerEmbedding,
)

__all__ = [
    "EmbeddingModel",
    "EmbeddingUnavailableError",
    "SentenceTransformerEmbedding",
]

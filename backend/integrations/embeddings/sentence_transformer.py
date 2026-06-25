"""sentence-transformers embedding model (lazy, process-cached).

Wraps a SentenceTransformer model. The library (and its torch dependency) is
heavy, so it is imported only when the model is first used. Until then the app —
and its test suite — runs without it: ``available()`` returns False and ingestion
records documents as ``unavailable`` instead of failing.
"""

from __future__ import annotations

import logging

from backend.integrations.embeddings.base import (
    EmbeddingModel,
    EmbeddingUnavailableError,
)

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding(EmbeddingModel):
    """Encode text with a local SentenceTransformer model."""

    def __init__(self, model_name: str, *, dimension_hint: int = 384) -> None:
        self._model_name = model_name
        self._dimension_hint = dimension_hint
        self._model = None  # loaded lazily on first encode

    def available(self) -> bool:
        try:
            import sentence_transformers  # noqa: F401
        except Exception:  # noqa: BLE001 — any import failure means unavailable
            return False
        return True

    @property
    def dimension(self) -> int:
        if self._model is not None:
            return int(self._model.get_sentence_embedding_dimension())
        return self._dimension_hint

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as exc:  # noqa: BLE001
                raise EmbeddingUnavailableError(
                    "sentence-transformers is not installed "
                    "(install backend/requirements-knowledge.txt)."
                ) from exc
            logger.info("Loading embedding model %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        vectors = model.encode(
            texts, convert_to_numpy=True, normalize_embeddings=True
        )
        return [vector.tolist() for vector in vectors]

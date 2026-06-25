"""Embedding model contract.

An ``EmbeddingModel`` is a thin integration wrapper: it turns text into vectors
and nothing else. Heavy model libraries are imported lazily by concrete
implementations so the app boots without them; ``available()`` reports whether
the backing library is installed, and ``encode`` raises
``EmbeddingUnavailableError`` when it is not — mirroring the voice + browser
integrations' graceful-degradation pattern.
"""

from abc import ABC, abstractmethod


class EmbeddingUnavailableError(RuntimeError):
    """Raised when an encode is attempted but the model library is missing."""


class EmbeddingModel(ABC):
    """Encodes text into dense vectors for semantic search."""

    @abstractmethod
    def available(self) -> bool:
        """Whether the backing library is importable (no network)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimension produced by ``encode``."""
        raise NotImplementedError

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts into vectors. Raises ``EmbeddingUnavailableError`` when
        the model library is not installed."""
        raise NotImplementedError

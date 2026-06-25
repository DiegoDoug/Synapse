"""AI provider integrations (thin LLM clients).

Each provider implements ``LLMProvider`` and wraps one vendor's HTTP/SDK
surface — no business logic, no database access. The service layer selects and
constructs a provider; routes never import these directly.
"""

from backend.integrations.ai.base import (
    LLMProvider,
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

__all__ = [
    "LLMProvider",
    "ProviderError",
    "ProviderAuthError",
    "ProviderRateLimitError",
    "ProviderUnavailableError",
]

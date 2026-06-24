"""Integration layer contracts.

Defines the minimal interface every external API client implements. Concrete
integrations (Gmail, Google Calendar) are thin HTTP/SDK wrappers — no business
logic, no database access. They are constructed by the service layer with the
credentials they need.
"""

from abc import ABC, abstractmethod


class Integration(ABC):
    """Base contract for an external API client."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Stable provider identifier (e.g. "google")."""
        raise NotImplementedError

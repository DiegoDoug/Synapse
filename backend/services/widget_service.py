"""Widget service — business logic for dashboard widgets.

Stage 4.5 needs exactly one widget write: updating a widget's configuration
through the confirmed ``update_widget_config`` tool. The service is the seam the
``ToolExecutor`` calls; it scopes every change to the owning user and talks only
to ``WidgetRepository``.
"""

from __future__ import annotations

from typing import Any

from backend.models.dashboard_widget import DashboardWidget
from backend.repositories.widget_repository import WidgetRepository


class WidgetService:
    """Read and reconfigure a user's dashboard widgets."""

    def __init__(self, widgets: WidgetRepository) -> None:
        self._widgets = widgets

    def list(self, user_id: int) -> list[DashboardWidget]:
        return self._widgets.list_for_user(user_id)

    def update_config(
        self,
        user_id: int,
        widget_id: int,
        config: dict[str, Any],
        *,
        merge: bool = True,
    ) -> DashboardWidget | None:
        """Update a widget's config. Returns None if not owned/found.

        ``merge`` (default) layers the supplied keys over the existing config;
        ``merge=False`` replaces it wholesale.
        """
        widget = self._owned(user_id, widget_id)
        if widget is None:
            return None
        widget.config = {**widget.config, **config} if merge else dict(config)
        return self._widgets.update(widget)

    def _owned(self, user_id: int, widget_id: int) -> DashboardWidget | None:
        row = self._widgets.get(widget_id)
        if row is None or row.user_id != user_id:
            return None
        return row

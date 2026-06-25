"""ToolExecutor — runs a write action through the service layer.

The single place where an assistant-proposed write actually executes, whether
it ran autonomously (a create) or after user approval (an update / delete). It
dispatches on the tool name to the owning service method and returns a small
result describing success or failure. It never touches repositories or
integrations directly — only services, per the architecture contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.schemas.task import TaskCreate, TaskUpdate
from backend.services.task_service import TaskService
from backend.services.widget_service import WidgetService


@dataclass
class ExecutionResult:
    """Outcome of running one action: a success flag plus a text message."""

    ok: bool
    message: str


class ToolExecutor:
    """Execute write tools by routing their payloads to services."""

    def __init__(self, tasks: TaskService, widgets: WidgetService) -> None:
        self._tasks = tasks
        self._widgets = widgets

    def execute(
        self, user_id: int, tool_name: str, payload: dict[str, Any]
    ) -> ExecutionResult:
        handler = self._handlers().get(tool_name)
        if handler is None:
            return ExecutionResult(False, f"No executor for tool '{tool_name}'.")
        return handler(user_id, payload)

    def _handlers(self):
        return {
            "create_task": self._create_task,
            "update_task": self._update_task,
            "delete_task": self._delete_task,
            "update_widget_config": self._update_widget_config,
        }

    # --- Task writes -------------------------------------------------------

    def _create_task(self, user_id: int, payload: dict[str, Any]) -> ExecutionResult:
        task = self._tasks.create(user_id, TaskCreate(**payload))
        return ExecutionResult(True, f"Created task #{task.id}: '{task.title}'.")

    def _update_task(self, user_id: int, payload: dict[str, Any]) -> ExecutionResult:
        data = dict(payload)
        task_id = data.pop("task_id", None)
        if task_id is None:
            return ExecutionResult(False, "update_task requires 'task_id'.")
        task = self._tasks.update(user_id, int(task_id), TaskUpdate(**data))
        if task is None:
            return ExecutionResult(False, f"Task #{task_id} not found.")
        return ExecutionResult(True, f"Updated task #{task.id}: '{task.title}'.")

    def _delete_task(self, user_id: int, payload: dict[str, Any]) -> ExecutionResult:
        task_id = payload.get("task_id")
        if task_id is None:
            return ExecutionResult(False, "delete_task requires 'task_id'.")
        if not self._tasks.delete(user_id, int(task_id)):
            return ExecutionResult(False, f"Task #{task_id} not found.")
        return ExecutionResult(True, f"Deleted task #{task_id}.")

    # --- Widget writes -----------------------------------------------------

    def _update_widget_config(
        self, user_id: int, payload: dict[str, Any]
    ) -> ExecutionResult:
        widget_id = payload.get("widget_id")
        config = payload.get("config")
        if widget_id is None or not isinstance(config, dict):
            return ExecutionResult(
                False, "update_widget_config requires 'widget_id' and 'config'."
            )
        widget = self._widgets.update_config(user_id, int(widget_id), config)
        if widget is None:
            return ExecutionResult(False, f"Widget #{widget_id} not found.")
        return ExecutionResult(True, f"Updated config for widget #{widget.id}.")

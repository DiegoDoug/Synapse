"""Write tools (Stage 4.5) — propose internal CRUD through the confirmation flow.

Each tool builds a ``ProposedAction`` and hands it to the ``ConfirmationService``
on the ``ToolContext``. Creates run immediately; updates and deletes are stored
as pending actions and surfaced to the user for approval. Tools never mutate
state themselves and never touch repositories or integrations — execution lives
in the ``ToolExecutor``. Like read tools, they return plain text for the model.
"""

from typing import Any

from backend.schemas.action import ProposedAction
from backend.services.tools.base import Tool, ToolContext

_NO_CONFIRMATION = (
    "Write tools are not available in this session (no confirmation service)."
)


class _WriteTool(Tool):
    """Shared plumbing: route a proposed action through the confirmation flow."""

    action_type: str

    def _propose(
        self,
        context: ToolContext,
        *,
        summary: str,
        payload: dict[str, Any],
    ) -> str:
        if context.confirmations is None:
            return _NO_CONFIRMATION
        action = ProposedAction(
            tool_name=self.name,
            action_type=self.action_type,
            summary=summary,
            payload=payload,
        )
        return context.confirmations.handle(context.user_id, action)


class CreateTaskTool(_WriteTool):
    """Create a personal task. Autonomous — runs without confirmation."""

    name = "create_task"
    action_type = "create"
    description = (
        "Create a new personal task / to-do for the user. Runs immediately "
        "without confirmation. Returns the created task's id."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short task title."},
            "description": {
                "type": "string",
                "description": "Optional longer details.",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high"],
                "description": "Task priority (default normal).",
            },
            "due_at": {
                "type": "string",
                "description": "Optional ISO-8601 due datetime.",
            },
        },
        "required": ["title"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        title = (arguments.get("title") or "").strip()
        if not title:
            return "create_task requires a non-empty 'title'."
        payload: dict[str, Any] = {"title": title}
        for key in ("description", "priority", "due_at"):
            value = arguments.get(key)
            if value:
                payload[key] = value
        return self._propose(
            context, summary=f"Create task '{title}'", payload=payload
        )


class UpdateTaskTool(_WriteTool):
    """Update a task. Requires user confirmation before it runs."""

    name = "update_task"
    action_type = "update"
    description = (
        "Update an existing task by id (title, description, status, priority, "
        "or due date). Requires the user's approval before it takes effect."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "Id of the task to update."},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["todo", "done"],
                "description": "Mark the task todo or done.",
            },
            "priority": {"type": "string", "enum": ["low", "normal", "high"]},
            "due_at": {"type": "string", "description": "ISO-8601 due datetime."},
        },
        "required": ["task_id"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        task_id = arguments.get("task_id")
        if task_id is None:
            return "update_task requires 'task_id'."
        payload: dict[str, Any] = {"task_id": int(task_id)}
        for key in ("title", "description", "status", "priority", "due_at"):
            if key in arguments and arguments[key] is not None:
                payload[key] = arguments[key]
        if len(payload) == 1:
            return "update_task needs at least one field to change."
        return self._propose(
            context, summary=f"Update task #{task_id}", payload=payload
        )


class DeleteTaskTool(_WriteTool):
    """Delete a task. Requires user confirmation before it runs."""

    name = "delete_task"
    action_type = "delete"
    description = (
        "Delete a task by id. Requires the user's approval before it takes "
        "effect."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task_id": {"type": "integer", "description": "Id of the task to delete."},
        },
        "required": ["task_id"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        task_id = arguments.get("task_id")
        if task_id is None:
            return "delete_task requires 'task_id'."
        return self._propose(
            context,
            summary=f"Delete task #{task_id}",
            payload={"task_id": int(task_id)},
        )


class UpdateWidgetConfigTool(_WriteTool):
    """Update a dashboard widget's config. Requires user confirmation."""

    name = "update_widget_config"
    action_type = "update"
    description = (
        "Update the configuration of a dashboard widget by id. 'config' is an "
        "object of settings merged over the widget's current config. Requires "
        "the user's approval before it takes effect."
    )
    parameters = {
        "type": "object",
        "properties": {
            "widget_id": {
                "type": "integer",
                "description": "Id of the widget to reconfigure.",
            },
            "config": {
                "type": "object",
                "description": "Settings to merge into the widget config.",
            },
        },
        "required": ["widget_id", "config"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        widget_id = arguments.get("widget_id")
        config = arguments.get("config")
        if widget_id is None or not isinstance(config, dict):
            return "update_widget_config requires 'widget_id' and a 'config' object."
        return self._propose(
            context,
            summary=f"Update widget #{widget_id} config",
            payload={"widget_id": int(widget_id), "config": config},
        )

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

    # External / browser writes force confirmation regardless of action_type.
    requires_confirmation: bool | None = None

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
            requires_confirmation=self.requires_confirmation,
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


# --- External / outbound write tools ----------------------------------------
# These always require confirmation: sending mail, touching an external
# calendar, messaging, or submitting a web form leaves the system and is not
# reversible, so the user approves each one regardless of action_type.


class SendEmailTool(_WriteTool):
    """Send an email via the user's connected Gmail account. Confirmed."""

    name = "send_email"
    action_type = "create"
    requires_confirmation = True
    description = (
        "Send an email from the user's connected Gmail account. Always requires "
        "the user's approval before it sends."
    )
    parameters = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string", "description": "Email subject line."},
            "body": {"type": "string", "description": "Plain-text email body."},
        },
        "required": ["to", "subject", "body"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        to = (arguments.get("to") or "").strip()
        if not to:
            return "send_email requires a 'to' address."
        return self._propose(
            context,
            summary=f"Send email to {to}",
            payload={
                "to": to,
                "subject": arguments.get("subject") or "",
                "body": arguments.get("body") or "",
            },
        )


class CreateCalendarEventTool(_WriteTool):
    """Create an event on the user's Google Calendar. Confirmed."""

    name = "create_calendar_event"
    action_type = "create"
    requires_confirmation = True
    description = (
        "Create an event on the user's connected Google Calendar. 'start' and "
        "'end' are ISO-8601: a date (YYYY-MM-DD) for all-day, or a datetime for "
        "a timed event. Always requires the user's approval before it is created."
    )
    parameters = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Event title."},
            "start": {"type": "string", "description": "ISO-8601 start date/datetime."},
            "end": {"type": "string", "description": "ISO-8601 end date/datetime."},
            "description": {"type": "string"},
            "location": {"type": "string"},
        },
        "required": ["summary", "start"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        summary = (arguments.get("summary") or "").strip()
        start = (arguments.get("start") or "").strip()
        if not summary or not start:
            return "create_calendar_event requires 'summary' and 'start'."
        payload: dict[str, Any] = {"summary": summary, "start": start}
        for key in ("end", "description", "location"):
            if arguments.get(key):
                payload[key] = arguments[key]
        return self._propose(
            context, summary=f"Create event '{summary}'", payload=payload
        )


class DeleteCalendarEventTool(_WriteTool):
    """Delete an event from the user's Google Calendar. Confirmed."""

    name = "delete_calendar_event"
    action_type = "delete"
    requires_confirmation = True
    description = (
        "Delete an event from the user's Google Calendar by its provider event "
        "id. Always requires the user's approval before it is deleted."
    )
    parameters = {
        "type": "object",
        "properties": {
            "event_id": {
                "type": "string",
                "description": "The calendar provider's event id.",
            },
        },
        "required": ["event_id"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        event_id = (arguments.get("event_id") or "").strip()
        if not event_id:
            return "delete_calendar_event requires 'event_id'."
        return self._propose(
            context,
            summary=f"Delete calendar event {event_id}",
            payload={"event_id": event_id},
        )


class SendTelegramMessageTool(_WriteTool):
    """Send a Telegram message via the user's bot. Confirmed."""

    name = "send_telegram_message"
    action_type = "create"
    requires_confirmation = True
    description = (
        "Send a message to the user over their configured Telegram bot. Always "
        "requires the user's approval before it sends."
    )
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Message text to send."},
            "chat_id": {
                "type": "string",
                "description": "Optional chat id; defaults to the configured chat.",
            },
        },
        "required": ["text"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        text = (arguments.get("text") or "").strip()
        if not text:
            return "send_telegram_message requires 'text'."
        payload: dict[str, Any] = {"text": text}
        if arguments.get("chat_id"):
            payload["chat_id"] = str(arguments["chat_id"])
        return self._propose(
            context, summary="Send a Telegram message", payload=payload
        )


class FillFormTool(_WriteTool):
    """Fill and submit a web form via the headless browser. Confirmed."""

    name = "fill_form"
    action_type = "update"
    requires_confirmation = True
    description = (
        "Fill in and submit a web form. 'fields' maps CSS selectors to the value "
        "to type into each. Optionally provide 'submit_selector' to click; "
        "otherwise Enter is pressed in the last field. Always requires the "
        "user's approval before it submits."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Absolute http(s) page URL."},
            "fields": {
                "type": "object",
                "description": "Map of CSS selector → value to fill.",
            },
            "submit_selector": {
                "type": "string",
                "description": "Optional CSS selector of the submit control.",
            },
        },
        "required": ["url", "fields"],
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        url = (arguments.get("url") or "").strip()
        fields = arguments.get("fields")
        if not url or not isinstance(fields, dict) or not fields:
            return "fill_form requires 'url' and a non-empty 'fields' object."
        payload: dict[str, Any] = {"url": url, "fields": fields}
        if arguments.get("submit_selector"):
            payload["submit_selector"] = arguments["submit_selector"]
        return self._propose(
            context, summary=f"Fill and submit a form on {url}", payload=payload
        )

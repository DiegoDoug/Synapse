"""Read-only tools over synced data (email, calendar, notifications).

Each tool aggregates across the current user's connected accounts via the
repositories carried on ``ToolContext`` and returns a compact text summary for
the model. No writes, no external API calls — only local synced rows.
"""

from datetime import UTC, datetime
from typing import Any

from backend.models.calendar_event import CalendarEvent
from backend.models.email_message import EmailMessage
from backend.services.tools.base import Tool, ToolContext

_MAX_LIMIT = 25


def _clamp(value: Any, default: int) -> int:
    try:
        return max(1, min(int(value), _MAX_LIMIT))
    except (TypeError, ValueError):
        return default


class SearchEmailsTool(Tool):
    """Find synced emails matching an optional text query."""

    name = "search_emails"
    description = (
        "Search the user's synced emails by an optional text query over the "
        "sender, subject, and snippet. Returns the most recent matches."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Case-insensitive text to match; omit for recent mail.",
            },
            "unread_only": {
                "type": "boolean",
                "description": "Restrict to unread messages.",
            },
            "limit": {"type": "integer", "description": "Max results (1-25)."},
        },
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        query = (arguments.get("query") or "").strip().lower()
        unread_only = bool(arguments.get("unread_only", False))
        limit = _clamp(arguments.get("limit"), 10)

        rows: list[EmailMessage] = []
        for account in context.accounts.list_for_user(context.user_id):
            rows.extend(
                context.emails.list_for_account(
                    account.id, limit=_MAX_LIMIT, unread_only=unread_only
                )
            )
        if query:
            rows = [r for r in rows if query in self._haystack(r)]
        rows.sort(key=lambda r: (r.received_at or datetime.min), reverse=True)
        rows = rows[:limit]

        if not rows:
            return "No matching emails found."
        return "\n".join(self._format(r) for r in rows)

    @staticmethod
    def _haystack(row: EmailMessage) -> str:
        return " ".join(
            filter(None, [row.sender, row.subject, row.snippet])
        ).lower()

    @staticmethod
    def _format(row: EmailMessage) -> str:
        flag = "" if row.is_read else "(unread) "
        when = row.received_at.strftime("%Y-%m-%d") if row.received_at else "—"
        return (
            f"- {flag}{when} | from {row.sender or 'unknown'} | "
            f"{row.subject or '(no subject)'}"
        )


class GetCalendarEventsTool(Tool):
    """List upcoming synced calendar events."""

    name = "get_calendar_events"
    description = (
        "List the user's upcoming synced calendar events, soonest first."
    )
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max events (1-25)."},
            "include_past": {
                "type": "boolean",
                "description": "Include events that already started.",
            },
        },
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        limit = _clamp(arguments.get("limit"), 10)
        include_past = bool(arguments.get("include_past", False))
        now = datetime.now(UTC)

        rows: list[CalendarEvent] = []
        for account in context.accounts.list_for_user(context.user_id):
            rows.extend(
                context.events.list_for_account(account.id, limit=_MAX_LIMIT)
            )
        if not include_past:
            rows = [r for r in rows if self._aware(r.start) >= now]
        rows.sort(key=lambda r: self._aware(r.start))
        rows = rows[:limit]

        if not rows:
            return "No upcoming events found."
        return "\n".join(self._format(r) for r in rows)

    @staticmethod
    def _aware(value: datetime | None) -> datetime:
        if value is None:
            return datetime.max.replace(tzinfo=UTC)
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    @classmethod
    def _format(cls, row: CalendarEvent) -> str:
        when = "all day" if row.all_day else cls._aware(row.start).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        location = f" @ {row.location}" if row.location else ""
        return f"- {when} | {row.summary or 'Untitled event'}{location}"


class GetNotificationsTool(Tool):
    """List the user's in-app notifications."""

    name = "get_notifications"
    description = (
        "List the user's in-app notifications (reminders, alerts, summaries)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "unread_only": {
                "type": "boolean",
                "description": "Restrict to unread notifications.",
            },
            "limit": {"type": "integer", "description": "Max results (1-25)."},
        },
    }

    def run(self, arguments: dict[str, Any], context: ToolContext) -> str:
        unread_only = bool(arguments.get("unread_only", False))
        limit = _clamp(arguments.get("limit"), 10)
        rows = context.notifications.list_for_user(
            context.user_id, limit=limit, unread_only=unread_only
        )
        if not rows:
            return "No notifications found."
        return "\n".join(
            f"- [{r.category}] {r.title}" + (f": {r.body}" if r.body else "")
            for r in rows
        )

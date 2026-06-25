"""ToolExecutor — runs a write action through the service layer.

The single place where an assistant-proposed write actually executes, whether
it ran autonomously (a create) or after user approval (everything else). It
dispatches on the tool name to the owning service method and returns a small
result describing success or failure. It never touches repositories (beyond
resolving the target account) or provider APIs directly — only services, per the
architecture contract.

Internal task/widget services are always present. External services (email,
calendar, messaging) and the browser are optional: when a capability is not
configured, its handler returns a friendly ``ExecutionResult`` instead of
raising, so an un-configured action fails cleanly rather than crashing a turn.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.integrations.browser.service import BrowserError, BrowserService
from backend.repositories.account_repository import AccountRepository
from backend.schemas.task import TaskCreate, TaskUpdate
from backend.services.calendar_service import CalendarService
from backend.services.email_service import EmailService
from backend.services.messaging_service import MessagingService
from backend.services.task_service import TaskService
from backend.services.widget_service import WidgetService

_GOOGLE = "google"


@dataclass
class ExecutionResult:
    """Outcome of running one action: a success flag plus a text message."""

    ok: bool
    message: str


class ToolExecutor:
    """Execute write tools by routing their payloads to services."""

    def __init__(
        self,
        tasks: TaskService,
        widgets: WidgetService,
        *,
        accounts: AccountRepository | None = None,
        email: EmailService | None = None,
        calendar: CalendarService | None = None,
        messaging: MessagingService | None = None,
        browser: BrowserService | None = None,
    ) -> None:
        self._tasks = tasks
        self._widgets = widgets
        self._accounts = accounts
        self._email = email
        self._calendar = calendar
        self._messaging = messaging
        self._browser = browser

    def execute(
        self, user_id: int, tool_name: str, payload: dict[str, Any]
    ) -> ExecutionResult:
        handler = self._handlers().get(tool_name)
        if handler is None:
            return ExecutionResult(False, f"No executor for tool '{tool_name}'.")
        try:
            return handler(user_id, payload)
        except Exception as exc:  # noqa: BLE001 — never raise out of execution
            return ExecutionResult(False, f"Action failed: {exc}")

    def _handlers(self):
        return {
            # Internal CRUD
            "create_task": self._create_task,
            "update_task": self._update_task,
            "delete_task": self._delete_task,
            "update_widget_config": self._update_widget_config,
            # External / outbound
            "send_email": self._send_email,
            "create_calendar_event": self._create_calendar_event,
            "delete_calendar_event": self._delete_calendar_event,
            "send_telegram_message": self._send_telegram_message,
            # Browser write
            "fill_form": self._fill_form,
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

    # --- External: email ---------------------------------------------------

    def _send_email(self, user_id: int, payload: dict[str, Any]) -> ExecutionResult:
        if self._email is None:
            return ExecutionResult(False, "Email sending is not configured.")
        to = payload.get("to")
        subject = payload.get("subject") or ""
        body = payload.get("body") or ""
        if not to:
            return ExecutionResult(False, "send_email requires 'to'.")
        account_id = self._resolve_account(user_id)
        if account_id is None:
            return ExecutionResult(False, "No connected Google account to send from.")
        message_id = self._email.send_email(
            account_id, to=to, subject=subject, body=body
        )
        return ExecutionResult(True, f"Email sent to {to} (id {message_id}).")

    # --- External: calendar ------------------------------------------------

    def _create_calendar_event(
        self, user_id: int, payload: dict[str, Any]
    ) -> ExecutionResult:
        if self._calendar is None:
            return ExecutionResult(False, "Calendar writes are not configured.")
        summary = payload.get("summary")
        start = payload.get("start")
        if not summary or not start:
            return ExecutionResult(
                False, "create_calendar_event requires 'summary' and 'start'."
            )
        account_id = self._resolve_account(user_id)
        if account_id is None:
            return ExecutionResult(False, "No connected Google account for calendar.")
        event_id = self._calendar.create_event(
            account_id,
            summary=summary,
            start=start,
            end=payload.get("end"),
            description=payload.get("description"),
            location=payload.get("location"),
        )
        return ExecutionResult(True, f"Created event '{summary}' (id {event_id}).")

    def _delete_calendar_event(
        self, user_id: int, payload: dict[str, Any]
    ) -> ExecutionResult:
        if self._calendar is None:
            return ExecutionResult(False, "Calendar writes are not configured.")
        external_id = payload.get("event_id")
        if not external_id:
            return ExecutionResult(False, "delete_calendar_event requires 'event_id'.")
        account_id = self._resolve_account(user_id)
        if account_id is None:
            return ExecutionResult(False, "No connected Google account for calendar.")
        self._calendar.delete_event(account_id, str(external_id))
        return ExecutionResult(True, f"Deleted calendar event {external_id}.")

    # --- External: messaging -----------------------------------------------

    def _send_telegram_message(
        self, user_id: int, payload: dict[str, Any]
    ) -> ExecutionResult:
        if self._messaging is None:
            return ExecutionResult(False, "Telegram messaging is not configured.")
        text = payload.get("text")
        if not text:
            return ExecutionResult(False, "send_telegram_message requires 'text'.")
        note = self._messaging.send_telegram_message(
            text, chat_id=payload.get("chat_id")
        )
        return ExecutionResult(True, note)

    # --- Browser write -----------------------------------------------------

    def _fill_form(self, user_id: int, payload: dict[str, Any]) -> ExecutionResult:
        if self._browser is None:
            return ExecutionResult(False, "Browser automation is not available.")
        url = payload.get("url")
        fields = payload.get("fields")
        if not url or not isinstance(fields, dict) or not fields:
            return ExecutionResult(
                False, "fill_form requires 'url' and a non-empty 'fields' object."
            )
        try:
            result_text = self._browser.fill_and_submit(
                url, fields, submit_selector=payload.get("submit_selector")
            )
        except BrowserError as exc:
            return ExecutionResult(False, f"Form submission failed: {exc}")
        preview = result_text[:200] + ("…" if len(result_text) > 200 else "")
        return ExecutionResult(True, f"Submitted form on {url}. Result: {preview}")

    # --- Internals ---------------------------------------------------------

    def _resolve_account(self, user_id: int) -> int | None:
        """Return the user's first connected Google account id, if any."""
        if self._accounts is None:
            return None
        for account in self._accounts.list_for_user(user_id):
            if account.provider == _GOOGLE:
                return account.id
        return None

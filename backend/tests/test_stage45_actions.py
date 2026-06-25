"""Stage 4.5 (Major Feature 1) tests — confirmation flow + internal write tools.

Covers the pending-action lifecycle end to end: write tools propose actions,
creates run autonomously, updates/deletes wait for approval, and the
ToolExecutor routes execution through the service layer. The AIService is driven
with an in-memory provider that requests a write tool, mirroring the Stage 4
tool-loop tests. No network or SDKs.
"""

import pytest
from backend.integrations.ai.base import LLMProvider
from backend.models.dashboard_widget import DashboardWidget
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.pending_action_repository import PendingActionRepository
from backend.repositories.system_prompt_repository import SystemPromptRepository
from backend.repositories.task_repository import TaskRepository
from backend.repositories.widget_repository import WidgetRepository
from backend.schemas.action import ProposedAction
from backend.schemas.ai import ChatResponse, ToolCall
from backend.schemas.task import TaskCreate
from backend.services.ai_service import AIService
from backend.services.confirmation_service import ConfirmationService
from backend.services.conversation_service import ConversationService
from backend.services.task_service import TaskService
from backend.services.tool_executor import ToolExecutor
from backend.services.tools.base import ToolContext
from backend.services.tools.registry import ToolRegistry
from backend.services.tools.write_tools import (
    CreateTaskTool,
    DeleteTaskTool,
    UpdateTaskTool,
    UpdateWidgetConfigTool,
)
from backend.services.widget_service import WidgetService
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# --- Builders ----------------------------------------------------------------


def _executor(session: Session) -> ToolExecutor:
    return ToolExecutor(
        TaskService(TaskRepository(session)),
        WidgetService(WidgetRepository(session)),
    )


def _confirmations(session: Session) -> ConfirmationService:
    return ConfirmationService(PendingActionRepository(session), _executor(session))


def _context(session: Session, confirmations: ConfirmationService) -> ToolContext:
    # Read repos aren't exercised here; pass the write seam only.
    return ToolContext(
        user_id=1,
        accounts=None,
        emails=None,
        events=None,
        notifications=None,
        confirmations=confirmations,
    )


# --- Fake provider -----------------------------------------------------------


class WriteToolProvider(LLMProvider):
    """Requests one write tool on the first turn, then answers."""

    def __init__(self, tool_name: str, arguments: dict) -> None:
        self._tool_name = tool_name
        self._arguments = arguments

    @property
    def provider(self) -> str:
        return "writefake"

    @property
    def model(self) -> str:
        return "wf-1"

    @property
    def supports_tools(self) -> bool:
        return True

    def chat(self, messages, *, system=None, tools=None, max_tokens, temperature):
        used = any(m.role == "tool" for m in messages)
        if tools and not used:
            return ChatResponse(
                content="",
                provider=self.provider,
                model=self.model,
                tool_calls=[
                    ToolCall(id="w1", name=self._tool_name, arguments=self._arguments)
                ],
            )
        return ChatResponse(content="Done.", provider=self.provider, model=self.model)


def _ai(session: Session) -> AIService:
    confirmations = _confirmations(session)
    registry = ToolRegistry(
        [CreateTaskTool(), UpdateTaskTool(), DeleteTaskTool(), UpdateWidgetConfigTool()],
        _context(session, confirmations),
    )
    return AIService(
        WriteToolProvider("create_task", {"title": "Buy milk"}),
        ConversationService(ConversationRepository(session)),
        SystemPromptRepository(session),
        max_tokens=128,
        temperature=0.5,
        tools=registry,
        confirmations=confirmations,
    )


# --- TaskService -------------------------------------------------------------


def test_task_service_crud(session):
    service = TaskService(TaskRepository(session))
    task = service.create(1, TaskCreate(title="Write report", priority="high"))
    assert task.id is not None and task.status == "todo"

    from backend.schemas.task import TaskUpdate

    updated = service.update(1, task.id, TaskUpdate(status="done"))
    assert updated.status == "done" and updated.completed_at is not None

    # Ownership is enforced: another user can't touch it.
    assert service.update(2, task.id, TaskUpdate(title="x")) is None
    assert service.delete(2, task.id) is False
    assert service.delete(1, task.id) is True
    assert service.get(1, task.id) is None


# --- ToolExecutor ------------------------------------------------------------


def test_executor_dispatches_and_reports_missing(session):
    executor = _executor(session)
    ok = executor.execute(1, "create_task", {"title": "Ship it"})
    assert ok.ok and "Created task" in ok.message

    missing = executor.execute(1, "update_task", {"task_id": 999, "title": "x"})
    assert not missing.ok and "not found" in missing.message

    unknown = executor.execute(1, "nope", {})
    assert not unknown.ok


def test_executor_updates_widget_config(session):
    widget = WidgetRepository(session).add(
        DashboardWidget(user_id=1, widget_type="tasks", title="Tasks")
    )
    result = _executor(session).execute(
        1, "update_widget_config", {"widget_id": widget.id, "config": {"limit": 5}}
    )
    assert result.ok
    assert WidgetRepository(session).get(widget.id).config == {"limit": 5}


# --- ConfirmationService routing --------------------------------------------


def test_create_is_autonomous(session):
    confirmations = _confirmations(session)
    msg = confirmations.handle(
        1,
        ProposedAction(
            tool_name="create_task",
            action_type="create",
            summary="Create task 'X'",
            payload={"title": "X"},
        ),
    )
    assert "Created task" in msg
    # Nothing is left pending for an autonomous create.
    assert confirmations.list(1, pending_only=True) == []
    assert confirmations.created_this_turn() == []


def test_update_requires_confirmation_then_approve(session):
    # Seed a task to update.
    task = TaskService(TaskRepository(session)).create(1, TaskCreate(title="Old"))
    confirmations = _confirmations(session)
    msg = confirmations.handle(
        1,
        ProposedAction(
            tool_name="update_task",
            action_type="update",
            summary=f"Update task #{task.id}",
            payload={"task_id": task.id, "title": "New"},
        ),
    )
    assert "awaiting" in msg.lower()

    pending = confirmations.list(1, pending_only=True)
    assert len(pending) == 1 and pending[0].status == "pending"

    approved = confirmations.approve(1, pending[0].id)
    assert approved.status == "executed"
    assert TaskService(TaskRepository(session)).get(1, task.id).title == "New"


def test_delete_reject_leaves_task(session):
    task = TaskService(TaskRepository(session)).create(1, TaskCreate(title="Keep"))
    confirmations = _confirmations(session)
    confirmations.handle(
        1,
        ProposedAction(
            tool_name="delete_task",
            action_type="delete",
            summary=f"Delete task #{task.id}",
            payload={"task_id": task.id},
        ),
    )
    action = confirmations.list(1, pending_only=True)[0]
    rejected = confirmations.reject(1, action.id)
    assert rejected.status == "rejected"
    # The task survives a rejection.
    assert TaskService(TaskRepository(session)).get(1, task.id) is not None


def test_approve_is_scoped_to_owner(session):
    task = TaskService(TaskRepository(session)).create(1, TaskCreate(title="Mine"))
    confirmations = _confirmations(session)
    confirmations.handle(
        1,
        ProposedAction(
            tool_name="delete_task",
            action_type="delete",
            summary="Delete",
            payload={"task_id": task.id},
        ),
    )
    action = confirmations.list(1, pending_only=True)[0]
    # A different user cannot approve someone else's pending action.
    assert confirmations.approve(2, action.id) is None


# --- Write tools -------------------------------------------------------------


def test_create_task_tool_runs_immediately(session):
    confirmations = _confirmations(session)
    out = CreateTaskTool().run({"title": "Inline"}, _context(session, confirmations))
    assert "Created task" in out


def test_update_task_tool_proposes(session):
    task = TaskService(TaskRepository(session)).create(1, TaskCreate(title="T"))
    confirmations = _confirmations(session)
    out = UpdateTaskTool().run(
        {"task_id": task.id, "status": "done"}, _context(session, confirmations)
    )
    assert "awaiting" in out.lower()
    assert len(confirmations.list(1, pending_only=True)) == 1


def test_write_tool_without_confirmation_service():
    ctx = ToolContext(
        user_id=1, accounts=None, emails=None, events=None, notifications=None
    )
    out = CreateTaskTool().run({"title": "X"}, ctx)
    assert "not available" in out.lower()


# --- AIService integration ---------------------------------------------------


def test_chat_autonomous_create_returns_no_pending(session):
    service = _ai(session)  # provider requests create_task
    result = service.chat(1, message="add a task to buy milk")
    assert result.message.content == "Done."
    assert result.pending_actions == []
    # The task really exists.
    assert TaskService(TaskRepository(session)).list(1)[0].title == "Buy milk"


def test_chat_update_surfaces_pending_action(session):
    task = TaskService(TaskRepository(session)).create(1, TaskCreate(title="Draft"))
    confirmations = _confirmations(session)
    registry = ToolRegistry(
        [UpdateTaskTool()], _context(session, confirmations)
    )
    service = AIService(
        WriteToolProvider("update_task", {"task_id": task.id, "title": "Final"}),
        ConversationService(ConversationRepository(session)),
        SystemPromptRepository(session),
        max_tokens=128,
        temperature=0.5,
        tools=registry,
        confirmations=confirmations,
    )
    result = service.chat(1, message="rename the draft task")
    assert len(result.pending_actions) == 1
    pa = result.pending_actions[0]
    assert pa.tool_name == "update_task" and pa.status == "pending"
    assert pa.conversation_id == result.conversation_id
    # Not executed yet — the title is unchanged until approval.
    assert TaskService(TaskRepository(session)).get(1, task.id).title == "Draft"


def test_stream_emits_pending_action_event(session):
    task = TaskService(TaskRepository(session)).create(1, TaskCreate(title="Draft"))
    confirmations = _confirmations(session)
    registry = ToolRegistry([DeleteTaskTool()], _context(session, confirmations))
    service = AIService(
        WriteToolProvider("delete_task", {"task_id": task.id}),
        ConversationService(ConversationRepository(session)),
        SystemPromptRepository(session),
        max_tokens=128,
        temperature=0.5,
        tools=registry,
        confirmations=confirmations,
    )
    events = list(service.stream(1, message="delete the draft"))
    types = [e["type"] for e in events]
    assert "pending_action" in types
    pending = next(e for e in events if e["type"] == "pending_action")
    assert pending["tool_name"] == "delete_task"

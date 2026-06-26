"""Stage 6 (Major Feature 1) tests — the agent framework + reference agent.

Covers the agent layer end to end without network or SDKs:

- the ``AgentRunRepository`` persists runs and ordered steps,
- the ``AgentRunner`` records plan → action → result steps and marks a run
  completed (or records an ``error`` step + ``failed`` run when an agent raises),
- ``AgentContext.act`` drives the shared ``ToolRegistry`` and flags a failed
  tool result without crashing the run (graceful degradation),
- the ``StudyAgent`` runs over the real read/write tools and creates a task
  through the autonomous-create path of the confirmation flow,
- ``AgentService`` lists agents, scopes runs to their owner, and rejects an
  unknown agent key.
"""

import pytest
from backend.agents.base import Agent, AgentContext
from backend.agents.registry import AgentRegistry, build_agent_registry
from backend.agents.runner import AgentRunner
from backend.agents.study_agent import StudyAgent
from backend.models.agent_run import (
    RUN_COMPLETED,
    RUN_FAILED,
    STEP_ACTION,
    STEP_PLAN,
    STEP_RESULT,
    AgentRun,
    AgentStep,
)
from backend.repositories.agent_run_repository import AgentRunRepository
from backend.repositories.task_repository import TaskRepository
from backend.services.agent_service import AgentService
from backend.services.factory import build_confirmation_service, build_tool_registry
from backend.services.task_service import TaskService
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


def _tools(session: Session):
    """Real user-scoped tool registry: read tools + write tools (confirmed),
    knowledge intentionally absent to exercise graceful degradation."""
    confirmations = build_confirmation_service(session, None)
    return build_tool_registry(session, user_id=1, confirmations=confirmations)


def _service(session: Session, registry: AgentRegistry | None = None) -> AgentService:
    runs = AgentRunRepository(session)
    return AgentService(
        registry or build_agent_registry(),
        AgentRunner(runs),
        runs,
        _tools(session),
    )


# --- Repository --------------------------------------------------------------


def test_repository_persists_runs_and_ordered_steps(session):
    repo = AgentRunRepository(session)
    run = repo.add_run(
        AgentRun(user_id=1, agent_key="study", agent_name="Study", input={})
    )
    assert run.id is not None

    for i, kind in enumerate((STEP_PLAN, STEP_ACTION, STEP_RESULT)):
        repo.add_step(AgentStep(run_id=run.id, step_index=i, kind=kind, title=kind))

    steps = repo.list_steps(run.id)
    assert [s.kind for s in steps] == [STEP_PLAN, STEP_ACTION, STEP_RESULT]
    assert [r.id for r in repo.list_for_user(1)] == [run.id]
    # Runs are scoped to their owner.
    assert repo.list_for_user(2) == []


# --- Runner ------------------------------------------------------------------


class _ProbeAgent(Agent):
    key = "probe"
    name = "Probe"
    description = "Calls one tool, then reports."

    def run(self, ctx: AgentContext) -> str:
        out = ctx.act("create_task", {"title": "From agent"}, title="Make a task")
        return f"done: {out}"


def test_runner_records_plan_action_result_and_completes(session):
    runs = AgentRunRepository(session)
    run = AgentRunner(runs).run(1, _ProbeAgent(), _tools(session), {})

    assert run.status == RUN_COMPLETED
    assert run.result.startswith("done:")
    assert run.finished_at is not None

    steps = runs.list_steps(run.id)
    assert [s.kind for s in steps] == [STEP_PLAN, STEP_ACTION, STEP_RESULT]
    action = steps[1]
    assert action.tool_name == "create_task" and action.status == "ok"
    # The action genuinely ran through the confirmation/executor path.
    assert TaskService(TaskRepository(session)).list(1)[0].title == "From agent"


class _BoomAgent(Agent):
    key = "boom"
    name = "Boom"
    description = "Raises."

    def run(self, ctx: AgentContext) -> str:
        raise RuntimeError("kaboom")


def test_runner_records_failure_without_crashing(session):
    runs = AgentRunRepository(session)
    run = AgentRunner(runs).run(1, _BoomAgent(), _tools(session), {})

    assert run.status == RUN_FAILED
    assert "kaboom" in run.error
    kinds = [s.kind for s in runs.list_steps(run.id)]
    assert kinds[0] == STEP_PLAN and kinds[-1] == "error"


class _UnknownToolAgent(Agent):
    key = "unknown"
    name = "Unknown"
    description = "Calls a tool that isn't registered."

    def run(self, ctx: AgentContext) -> str:
        return ctx.act("does_not_exist", {}, title="Try missing tool")


def test_unavailable_tool_is_flagged_but_run_completes(session):
    runs = AgentRunRepository(session)
    run = AgentRunner(runs).run(1, _UnknownToolAgent(), _tools(session), {})

    # Graceful degradation: the run completes, the step is flagged failed.
    assert run.status == RUN_COMPLETED
    action = runs.list_steps(run.id)[1]
    assert action.kind == STEP_ACTION and action.status == "failed"


# --- StudyAgent (reference) + AgentService -----------------------------------


def test_study_agent_runs_end_to_end_and_creates_task(session):
    service = _service(session)
    run = service.start(1, "study", {"topic": "Calculus"})

    assert run is not None and run.status == RUN_COMPLETED
    tool_steps = [s for s in run.steps if s.kind == STEP_ACTION]
    assert [s.tool_name for s in tool_steps] == [
        "get_calendar_events",
        "search_knowledge",
        "create_task",
    ]
    # The autonomous create really produced a task.
    tasks = TaskService(TaskRepository(session)).list(1)
    assert any(t.title == "Study: Calculus" for t in tasks)
    # Knowledge is absent here, so that step degrades to a failed action while
    # the run as a whole still succeeds.
    knowledge_step = next(s for s in tool_steps if s.tool_name == "search_knowledge")
    assert knowledge_step.status == "failed"


def test_service_lists_agents_and_run_is_owner_scoped(session):
    service = _service(session)
    catalogue = service.list_agents()
    assert any(a.key == "study" for a in catalogue)
    study = next(a for a in catalogue if a.key == "study")
    assert study.parameters and study.parameters[0].name == "topic"

    run = service.start(1, "study", {})
    assert service.get_run(1, run.id) is not None
    # A different user cannot read someone else's run.
    assert service.get_run(2, run.id) is None
    assert [r.id for r in service.list_runs(1)] == [run.id]
    assert service.list_runs(2) == []


def test_unknown_agent_key_returns_none(session):
    assert _service(session).start(1, "nope", {}) is None


def test_default_registry_exposes_study_agent():
    registry = build_agent_registry()
    assert isinstance(registry.get("study"), StudyAgent)
    assert registry.get("missing") is None

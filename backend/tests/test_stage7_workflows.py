"""Stage 7 (Major Feature 1) tests — scheduled execution + the workflow model.

Covers the automation layer end to end without a live scheduler or network:

- the ``WorkflowRepository`` persists definitions and runs and cascades a
  delete to the run history,
- the ``WorkflowService`` validates the schedule personalization (interval needs
  a frequency, a daily schedule needs a time, manual clears both), scopes every
  definition to its owner, and rejects an unknown agent,
- running a workflow on demand hands off to the Stage 6 agent layer, records the
  outcome, links the ``AgentRun`` for the audit trail, and bumps the tally,
- the ``max_runs`` cap auto-disables a workflow once reached,
- enabling a manual workflow is refused (nothing to schedule),
- the ``WorkflowScheduler`` registers a job for an enabled timed workflow and
  removes it when the workflow is manual/disabled.
"""

import pytest
from backend.agents.registry import build_agent_registry
from backend.agents.runner import AgentRunner
from backend.models.workflow import (
    SCHEDULE_CRON,
    SCHEDULE_INTERVAL,
    SCHEDULE_MANUAL,
    TRIGGER_MANUAL,
    WF_RUN_COMPLETED,
    Workflow,
    WorkflowRun,
)
from backend.repositories.agent_run_repository import AgentRunRepository
from backend.repositories.workflow_repository import WorkflowRepository
from backend.schemas.workflow import WorkflowCreate, WorkflowUpdate
from backend.services.agent_service import AgentService
from backend.services.factory import build_confirmation_service, build_tool_registry
from backend.services.workflow_scheduler import WorkflowScheduler
from backend.services.workflow_service import WorkflowError, WorkflowService
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


def _agent_service(session: Session) -> AgentService:
    confirmations = build_confirmation_service(session, None)
    tools = build_tool_registry(session, user_id=1, confirmations=confirmations)
    runs = AgentRunRepository(session)
    return AgentService(build_agent_registry(), AgentRunner(runs), runs, tools)


def _service(
    session: Session, scheduler: WorkflowScheduler | None = None
) -> WorkflowService:
    return WorkflowService(
        WorkflowRepository(session), _agent_service(session), scheduler
    )


def _interval_create(**over) -> WorkflowCreate:
    base = dict(
        name="Triage inbox",
        agent_key="email",
        params={"query": "invoice"},
        schedule_kind=SCHEDULE_INTERVAL,
        interval_minutes=30,
    )
    base.update(over)
    return WorkflowCreate(**base)


class _FakeScheduler:
    """Records APScheduler calls so we can assert sync/remove without a runtime."""

    def __init__(self) -> None:
        self.added: list[str] = []
        self.removed: list[str] = []

    def add_job(self, *_args, **kwargs) -> None:
        self.added.append(kwargs["id"])

    def remove_job(self, job_id: str) -> None:
        self.removed.append(job_id)


# --- Repository --------------------------------------------------------------


def test_repository_persists_and_cascades_delete(session):
    repo = WorkflowRepository(session)
    wf = repo.add(Workflow(user_id=1, name="W", agent_key="study"))
    assert wf.id is not None

    repo.add_run(WorkflowRun(workflow_id=wf.id, user_id=1))
    repo.add_run(WorkflowRun(workflow_id=wf.id, user_id=1))
    assert len(repo.list_runs(wf.id)) == 2

    repo.delete(wf)
    assert repo.get(wf.id) is None
    assert repo.list_runs(wf.id) == []


def test_repository_lists_enabled_only(session):
    repo = WorkflowRepository(session)
    repo.add(Workflow(user_id=1, name="on", agent_key="study", enabled=True))
    repo.add(Workflow(user_id=1, name="off", agent_key="study", enabled=False))
    assert [w.name for w in repo.list_enabled()] == ["on"]


# --- Schedule validation -----------------------------------------------------


def test_interval_requires_frequency(session):
    with pytest.raises(WorkflowError):
        _service(session).create_workflow(
            1, _interval_create(interval_minutes=None)
        )


def test_cron_requires_time_and_clears_interval(session):
    service = _service(session)
    with pytest.raises(WorkflowError):
        service.create_workflow(
            1, _interval_create(schedule_kind=SCHEDULE_CRON, interval_minutes=None)
        )

    wf = service.create_workflow(
        1,
        _interval_create(
            schedule_kind=SCHEDULE_CRON,
            interval_minutes=15,  # ignored for cron
            cron_hour=9,
            cron_minute=30,
        ),
    )
    assert wf.cron_hour == 9 and wf.cron_minute == 30
    assert wf.interval_minutes is None  # normalized away


def test_manual_workflow_is_never_enabled(session):
    wf = _service(session).create_workflow(
        1,
        WorkflowCreate(
            name="On demand",
            agent_key="study",
            schedule_kind=SCHEDULE_MANUAL,
            enabled=True,  # requested, but manual has nothing to schedule
        ),
    )
    assert wf.enabled is False
    assert wf.interval_minutes is None and wf.cron_hour is None


def test_unknown_agent_is_rejected(session):
    with pytest.raises(WorkflowError):
        _service(session).create_workflow(
            1, _interval_create(agent_key="does_not_exist")
        )


# --- Owner scoping -----------------------------------------------------------


def test_definitions_are_owner_scoped(session):
    service = _service(session)
    wf = service.create_workflow(1, _interval_create())
    assert service.get_workflow(2, wf.id) is None
    assert service.list_workflows(2) == []
    assert service.update_workflow(2, wf.id, WorkflowUpdate(name="hijack")) is None
    assert service.run_now(2, wf.id) is None
    assert service.delete_workflow(2, wf.id) is False


# --- Execution ---------------------------------------------------------------


def test_run_now_drives_agent_and_records_outcome(session):
    service = _service(session)
    wf = service.create_workflow(
        1,
        WorkflowCreate(name="Study run", agent_key="study", params={"topic": "Calc"}),
    )

    run = service.run_now(1, wf.id)
    assert run is not None
    assert run.status == WF_RUN_COMPLETED
    assert run.trigger == TRIGGER_MANUAL
    # The run links into the Stage 6 agent audit trail (no duplication).
    assert run.agent_run_id is not None

    # The tally advanced and the run is visible in history.
    refreshed = service.get_workflow(1, wf.id)
    assert refreshed.run_count == 1 and refreshed.last_run_at is not None
    assert [r.id for r in service.list_runs(1, wf.id)] == [run.id]


def test_unknown_agent_after_definition_fails_gracefully(session):
    """A run never raises — a bad target is captured on the run record."""
    service = _service(session)
    wf = service.create_workflow(1, WorkflowCreate(name="W", agent_key="study"))
    # Corrupt the stored target to simulate an agent that vanished.
    stored = WorkflowRepository(session).get(wf.id)
    stored.agent_key = "ghost"
    WorkflowRepository(session).update(stored)

    run = service.run_now(1, wf.id)
    assert run is not None and run.status == "failed"
    assert "ghost" in run.error


def test_max_runs_cap_auto_disables(session):
    scheduler = WorkflowScheduler(_FakeScheduler())
    service = _service(session, scheduler)
    wf = service.create_workflow(
        1, _interval_create(max_runs=2, enabled=True)
    )
    assert wf.enabled is True

    service.run_now(1, wf.id)
    assert service.get_workflow(1, wf.id).enabled is True  # 1 of 2
    service.run_now(1, wf.id)
    refreshed = service.get_workflow(1, wf.id)
    assert refreshed.run_count == 2 and refreshed.enabled is False  # cap reached


# --- Enable/disable ----------------------------------------------------------


def test_enabling_manual_workflow_is_refused(session):
    service = _service(session)
    wf = service.create_workflow(
        1, WorkflowCreate(name="W", agent_key="study", schedule_kind=SCHEDULE_MANUAL)
    )
    with pytest.raises(WorkflowError):
        service.set_enabled(1, wf.id, True)


# --- Scheduler adapter -------------------------------------------------------


def test_scheduler_registers_enabled_timed_workflow(session):
    fake = _FakeScheduler()
    scheduler = WorkflowScheduler(fake)
    service = _service(session, scheduler)

    wf = service.create_workflow(1, _interval_create(enabled=True))
    job_id = WorkflowScheduler.job_id(wf.id)
    assert job_id in fake.added

    # Disabling drops the live job.
    fake.added.clear()
    service.set_enabled(1, wf.id, False)
    assert job_id in fake.removed
    assert fake.added == []


def test_scheduler_ignores_manual_workflow(session):
    fake = _FakeScheduler()
    service = _service(session, WorkflowScheduler(fake))
    service.create_workflow(
        1, WorkflowCreate(name="W", agent_key="study", schedule_kind=SCHEDULE_MANUAL)
    )
    assert fake.added == []  # nothing scheduled for a manual workflow

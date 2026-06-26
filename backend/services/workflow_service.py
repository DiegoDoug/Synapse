"""WorkflowService — the API-facing facade over the automation layer.

Owns the workflow lifecycle: list/create/update/delete definitions, enable or
disable a schedule, run a workflow on demand, and read its run history. It is
orchestration on top of what already exists — a run is executed by handing off
to the Stage 6 ``AgentService`` (so the agent loop, the confirmation flow, and
the ``AgentRun`` audit trail are reused unchanged); this layer adds no new
side-effect path.

It also keeps the live schedule in sync: whenever a definition changes it asks
the ``WorkflowScheduler`` to (re)register or drop the job. When no scheduler is
present (scheduling disabled) it still persists definitions and runs on demand —
graceful degradation, never a crash.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.models.workflow import (
    SCHEDULE_CRON,
    SCHEDULE_INTERVAL,
    SCHEDULE_MANUAL,
    TARGET_AGENT,
    TRIGGER_MANUAL,
    WF_RUN_COMPLETED,
    WF_RUN_FAILED,
    WF_RUN_RUNNING,
    Workflow,
    WorkflowRun,
)
from backend.repositories.workflow_repository import WorkflowRepository
from backend.schemas.workflow import (
    WorkflowCreate,
    WorkflowRead,
    WorkflowRunRead,
    WorkflowUpdate,
)
from backend.services.agent_service import AgentService
from backend.services.workflow_scheduler import WorkflowScheduler

_VALID_SCHEDULES = {SCHEDULE_MANUAL, SCHEDULE_INTERVAL, SCHEDULE_CRON}


class WorkflowError(ValueError):
    """A bad workflow definition (surfaced as HTTP 400 by the route)."""


class WorkflowService:
    """Manage workflow definitions, schedules, and on-demand/scheduled runs."""

    def __init__(
        self,
        workflows: WorkflowRepository,
        agents: AgentService,
        scheduler: WorkflowScheduler | None = None,
    ) -> None:
        self._repo = workflows
        self._agents = agents
        self._scheduler = scheduler

    # --- Definitions -------------------------------------------------------

    def list_workflows(self, user_id: int) -> list[WorkflowRead]:
        return [_read(w) for w in self._repo.list_for_user(user_id)]

    def get_workflow(self, user_id: int, workflow_id: int) -> WorkflowRead | None:
        workflow = self._owned(user_id, workflow_id)
        return _read(workflow) if workflow else None

    def create_workflow(
        self, user_id: int, data: WorkflowCreate
    ) -> WorkflowRead:
        self._validate_agent(data.agent_key)
        workflow = Workflow(
            user_id=user_id,
            name=data.name,
            description=data.description,
            target_kind=TARGET_AGENT,
            agent_key=data.agent_key,
            params=data.params,
            schedule_kind=data.schedule_kind,
            interval_minutes=data.interval_minutes,
            cron_hour=data.cron_hour,
            cron_minute=data.cron_minute,
            max_runs=data.max_runs,
            enabled=data.enabled,
        )
        self._normalize_and_validate(workflow)
        workflow = self._repo.add(workflow)
        self._sync(workflow)
        return _read(workflow)

    def update_workflow(
        self, user_id: int, workflow_id: int, data: WorkflowUpdate
    ) -> WorkflowRead | None:
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        fields = data.model_dump(exclude_unset=True)
        if "agent_key" in fields:
            self._validate_agent(fields["agent_key"])
        for key, value in fields.items():
            setattr(workflow, key, value)
        workflow.updated_at = datetime.now(UTC)
        self._normalize_and_validate(workflow)
        workflow = self._repo.update(workflow)
        self._sync(workflow)
        return _read(workflow)

    def delete_workflow(self, user_id: int, workflow_id: int) -> bool:
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return False
        if self._scheduler is not None:
            self._scheduler.remove(workflow_id)
        self._repo.delete(workflow)
        return True

    def set_enabled(
        self, user_id: int, workflow_id: int, enabled: bool
    ) -> WorkflowRead | None:
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        if enabled and workflow.schedule_kind == SCHEDULE_MANUAL:
            raise WorkflowError(
                "A manual workflow has no schedule to enable; set an interval "
                "or daily time first."
            )
        workflow.enabled = enabled
        workflow.updated_at = datetime.now(UTC)
        workflow = self._repo.update(workflow)
        self._sync(workflow)
        return _read(workflow)

    # --- Execution ---------------------------------------------------------

    def run_now(
        self, user_id: int, workflow_id: int
    ) -> WorkflowRunRead | None:
        """Run a workflow immediately on the user's behalf."""
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        return _run_read(self.execute(workflow, trigger=TRIGGER_MANUAL))

    def execute_by_id(
        self, workflow_id: int, *, trigger: str
    ) -> WorkflowRun | None:
        """Load a workflow by id and execute it (the scheduler entry point).

        Not user-scoped: a scheduler tick is system-initiated and acts on the
        workflow's own owner. Returns None when the workflow no longer exists.
        """
        workflow = self._repo.get(workflow_id)
        if workflow is None:
            return None
        return self.execute(workflow, trigger=trigger)

    def execute(self, workflow: Workflow, *, trigger: str) -> WorkflowRun:
        """Execute a workflow once, recording the outcome and updating the tally.

        Reused by both the on-demand path and the scheduled job. A failure is
        captured on the run rather than raised, so a scheduled tick never tears
        down the scheduler.
        """
        run = self._repo.add_run(
            WorkflowRun(
                workflow_id=workflow.id,
                user_id=workflow.user_id,
                trigger=trigger,
                status=WF_RUN_RUNNING,
            )
        )
        try:
            self._run_target(workflow, run)
        except Exception as exc:  # noqa: BLE001 — a run must never crash the caller
            run.status = WF_RUN_FAILED
            run.error = f"{type(exc).__name__}: {exc}"

        run.finished_at = datetime.now(UTC)
        run = self._repo.update_run(run)
        self._record_execution(workflow)
        return run

    def list_runs(
        self, user_id: int, workflow_id: int, *, limit: int = 50
    ) -> list[WorkflowRunRead] | None:
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        return [_run_read(r) for r in self._repo.list_runs(workflow.id, limit=limit)]

    # --- Internals ---------------------------------------------------------

    def _run_target(self, workflow: Workflow, run: WorkflowRun) -> None:
        """Drive the workflow's target and fold its outcome onto the run."""
        if workflow.target_kind != TARGET_AGENT:
            raise WorkflowError(f"Unsupported target '{workflow.target_kind}'")

        agent_run = self._agents.start(
            workflow.user_id, workflow.agent_key, workflow.params or {}
        )
        if agent_run is None:
            run.status = WF_RUN_FAILED
            run.error = f"Unknown agent '{workflow.agent_key}'"
            return

        run.agent_run_id = agent_run.id
        if agent_run.status == WF_RUN_COMPLETED:
            run.status = WF_RUN_COMPLETED
            run.result = agent_run.result
        else:
            run.status = WF_RUN_FAILED
            run.error = agent_run.error or "Agent run failed"

    def _record_execution(self, workflow: Workflow) -> None:
        """Bump the run tally and auto-disable once the cap is reached."""
        workflow.run_count += 1
        workflow.last_run_at = datetime.now(UTC)
        if workflow.max_runs is not None and workflow.run_count >= workflow.max_runs:
            workflow.enabled = False
            if self._scheduler is not None:
                self._scheduler.remove(workflow.id)
        self._repo.update(workflow)

    def _owned(self, user_id: int, workflow_id: int) -> Workflow | None:
        workflow = self._repo.get(workflow_id)
        if workflow is None or workflow.user_id != user_id:
            return None
        return workflow

    def _validate_agent(self, agent_key: str) -> None:
        keys = {a.key for a in self._agents.list_agents()}
        if agent_key not in keys:
            raise WorkflowError(f"Unknown agent '{agent_key}'")

    def _normalize_and_validate(self, workflow: Workflow) -> None:
        """Enforce schedule-field combinations and clear irrelevant fields."""
        if workflow.schedule_kind not in _VALID_SCHEDULES:
            raise WorkflowError(f"Unknown schedule kind '{workflow.schedule_kind}'")

        if workflow.schedule_kind == SCHEDULE_INTERVAL:
            if not workflow.interval_minutes:
                raise WorkflowError(
                    "An interval schedule needs interval_minutes (how often to run)."
                )
            workflow.cron_hour = workflow.cron_minute = None
        elif workflow.schedule_kind == SCHEDULE_CRON:
            if workflow.cron_hour is None:
                raise WorkflowError(
                    "A daily schedule needs cron_hour (the time of day to run)."
                )
            workflow.cron_minute = workflow.cron_minute or 0
            workflow.interval_minutes = None
        else:  # manual
            workflow.interval_minutes = None
            workflow.cron_hour = workflow.cron_minute = None
            workflow.enabled = False  # nothing to schedule

    def _sync(self, workflow: Workflow) -> None:
        if self._scheduler is not None:
            self._scheduler.sync(workflow)


# --- Mappers -----------------------------------------------------------------


def _read(workflow: Workflow) -> WorkflowRead:
    return WorkflowRead(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        target_kind=workflow.target_kind,
        agent_key=workflow.agent_key,
        params=workflow.params,
        schedule_kind=workflow.schedule_kind,
        interval_minutes=workflow.interval_minutes,
        cron_hour=workflow.cron_hour,
        cron_minute=workflow.cron_minute,
        max_runs=workflow.max_runs,
        enabled=workflow.enabled,
        run_count=workflow.run_count,
        last_run_at=workflow.last_run_at,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _run_read(run: WorkflowRun) -> WorkflowRunRead:
    return WorkflowRunRead(
        id=run.id,
        workflow_id=run.workflow_id,
        trigger=run.trigger,
        status=run.status,
        result=run.result,
        error=run.error,
        agent_run_id=run.agent_run_id,
        created_at=run.created_at,
        finished_at=run.finished_at,
    )

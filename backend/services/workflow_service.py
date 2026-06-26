"""WorkflowService — the API-facing facade over the automation layer.

Owns the workflow lifecycle: list/create/update/delete definitions, enable or
disable a schedule/trigger, run a workflow on demand, and read its run history.
A workflow is a composed sequence of steps (the composer); executing it walks the
sequence, running each step by handing off to the Stage 6 ``AgentService`` (agent
steps) or the shared ``ToolRegistry`` (tool steps) — so the agent loop, the
confirmation flow, and the ``AgentRun`` audit trail are reused unchanged. Each
step's outcome is recorded as a ``WorkflowRunStep`` for step-level visibility;
this layer adds no new side-effect path.

It also evaluates event triggers against already-synced data (never integrations)
and keeps the live schedule in sync: whenever a definition changes it asks the
``WorkflowScheduler`` to (re)register or drop the per-workflow job. When no
scheduler is present (scheduling disabled) it still persists definitions and runs
on demand — graceful degradation, never a crash.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session

from backend.models.workflow import (
    SCHEDULE_CRON,
    SCHEDULE_EVENT,
    SCHEDULE_INTERVAL,
    SCHEDULE_MANUAL,
    STEP_AGENT,
    STEP_TOOL,
    TRIGGER_EVENT,
    TRIGGER_MANUAL,
    WF_RUN_COMPLETED,
    WF_RUN_FAILED,
    WF_RUN_RUNNING,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStep,
)
from backend.repositories.workflow_repository import WorkflowRepository
from backend.schemas.workflow import (
    CatalogueEntry,
    CatalogueEvent,
    CatalogueParam,
    WorkflowCatalogue,
    WorkflowCreate,
    WorkflowRead,
    WorkflowRunRead,
    WorkflowRunStepRead,
    WorkflowStepInput,
    WorkflowStepRead,
    WorkflowUpdate,
)
from backend.services.agent_service import AgentService
from backend.services.tools.registry import ToolRegistry
from backend.services.workflow_events import EVENT_LABELS, EVENT_TYPES, current_mark
from backend.services.workflow_scheduler import WorkflowScheduler

_VALID_SCHEDULES = {
    SCHEDULE_MANUAL,
    SCHEDULE_INTERVAL,
    SCHEDULE_CRON,
    SCHEDULE_EVENT,
}
_STEP_KINDS = {STEP_AGENT, STEP_TOOL}
# ToolRegistry.execute sentinels that mark a failed tool call (it never raises).
_TOOL_ERROR_PREFIXES = ("Unknown tool:", "Tool '")


class WorkflowError(ValueError):
    """A bad workflow definition (surfaced as HTTP 400 by the route)."""


class WorkflowService:
    """Manage workflow definitions, schedules/triggers, and executions."""

    def __init__(
        self,
        workflows: WorkflowRepository,
        agents: AgentService,
        tools: ToolRegistry,
        scheduler: WorkflowScheduler | None = None,
        session: Session | None = None,
    ) -> None:
        self._repo = workflows
        self._agents = agents
        self._tools = tools
        self._scheduler = scheduler
        # Used only to compute event high-water marks for event triggers.
        self._session = session

    # --- Catalogue ---------------------------------------------------------

    def catalogue(self) -> WorkflowCatalogue:
        """The agents, tools, and events the composer can pick from."""
        agents = [
            CatalogueEntry(
                kind=STEP_AGENT,
                ref=a.key,
                name=a.name,
                description=a.description,
                parameters=[
                    CatalogueParam(
                        name=p.name, description=p.description, required=p.required
                    )
                    for p in a.parameters
                ],
            )
            for a in self._agents.list_agents()
        ]
        tools = [
            CatalogueEntry(
                kind=STEP_TOOL,
                ref=spec.name,
                name=spec.name,
                description=spec.description,
                parameters=_tool_params(spec.parameters),
            )
            for spec in self._tools.specs()
        ]
        events = [
            CatalogueEvent(event_type=e, label=EVENT_LABELS[e]) for e in EVENT_TYPES
        ]
        return WorkflowCatalogue(steps=agents + tools, events=events)

    # --- Definitions -------------------------------------------------------

    def list_workflows(self, user_id: int) -> list[WorkflowRead]:
        return [self._read(w) for w in self._repo.list_for_user(user_id)]

    def get_workflow(self, user_id: int, workflow_id: int) -> WorkflowRead | None:
        workflow = self._owned(user_id, workflow_id)
        return self._read(workflow) if workflow else None

    def create_workflow(self, user_id: int, data: WorkflowCreate) -> WorkflowRead:
        steps = self._resolve_input_steps(data.steps, data.agent_key, data.params)
        self._validate_steps(steps)
        workflow = Workflow(
            user_id=user_id,
            name=data.name,
            description=data.description,
            agent_key=_primary_agent_ref(steps),
            schedule_kind=data.schedule_kind,
            interval_minutes=data.interval_minutes,
            cron_hour=data.cron_hour,
            cron_minute=data.cron_minute,
            event_type=data.event_type,
            max_runs=data.max_runs,
            enabled=data.enabled,
        )
        self._normalize_and_validate(workflow)
        workflow = self._repo.add(workflow)
        self._repo.replace_steps(workflow.id, _to_step_rows(steps))
        self._arm_if_event(workflow)
        self._sync(workflow)
        return self._read(workflow)

    def update_workflow(
        self, user_id: int, workflow_id: int, data: WorkflowUpdate
    ) -> WorkflowRead | None:
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        fields = data.model_dump(exclude_unset=True)
        steps_in = fields.pop("steps", None)
        agent_key = fields.pop("agent_key", None)
        params = fields.pop("params", None)

        for key, value in fields.items():
            setattr(workflow, key, value)

        # Recompose the sequence only when steps (or the legacy shortcut) change.
        if steps_in is not None or agent_key is not None:
            steps = self._resolve_input_steps(
                [WorkflowStepInput(**s) for s in (steps_in or [])],
                agent_key,
                params or {},
            )
            self._validate_steps(steps)
            self._repo.replace_steps(workflow.id, _to_step_rows(steps))
            workflow.agent_key = _primary_agent_ref(steps)

        workflow.updated_at = datetime.now(UTC)
        self._normalize_and_validate(workflow)
        workflow = self._repo.update(workflow)
        self._arm_if_event(workflow)
        self._sync(workflow)
        return self._read(workflow)

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
                "A manual workflow has no schedule to enable; set an interval, "
                "a daily time, or an event trigger first."
            )
        workflow.enabled = enabled
        workflow.updated_at = datetime.now(UTC)
        workflow = self._repo.update(workflow)
        self._arm_if_event(workflow)
        self._sync(workflow)
        return self._read(workflow)

    # --- Execution ---------------------------------------------------------

    def run_now(self, user_id: int, workflow_id: int) -> WorkflowRunRead | None:
        """Run a workflow immediately on the user's behalf."""
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        return self._run_read(self.execute(workflow, trigger=TRIGGER_MANUAL))

    def execute_by_id(
        self, workflow_id: int, *, trigger: str
    ) -> WorkflowRun | None:
        """Load a workflow by id and execute it (the scheduler entry point)."""
        workflow = self._repo.get(workflow_id)
        if workflow is None:
            return None
        return self.execute(workflow, trigger=trigger)

    def execute(self, workflow: Workflow, *, trigger: str) -> WorkflowRun:
        """Execute a workflow's step sequence once, recording every outcome.

        A failure is captured on the run/step rather than raised, so a scheduled
        tick or event evaluation never tears down the scheduler.
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
            self._run_sequence(workflow, run)
        except Exception as exc:  # noqa: BLE001 — a run must never crash the caller
            run.status = WF_RUN_FAILED
            run.error = f"{type(exc).__name__}: {exc}"

        run.finished_at = datetime.now(UTC)
        run = self._repo.update_run(run)
        self._record_execution(workflow)
        return run

    def evaluate_events(self) -> int:
        """Fire each event workflow whose source has new data; return # fired.

        Compares the source's current high-water mark to the workflow's cursor.
        A workflow with no cursor yet is *armed* to the current mark (so it never
        fires for the existing backlog) and fires only on subsequently synced
        data.
        """
        if self._session is None:
            return 0
        fired = 0
        for workflow in self._repo.list_enabled_events():
            if not workflow.event_type:
                continue
            mark = current_mark(self._session, workflow.user_id, workflow.event_type)
            if workflow.event_cursor is None:
                workflow.event_cursor = mark
                self._repo.update(workflow)
                continue
            if mark > workflow.event_cursor:
                # Advance before executing; the cursor persists with the tally.
                workflow.event_cursor = mark
                self.execute(workflow, trigger=TRIGGER_EVENT)
                fired += 1
        return fired

    def list_runs(
        self, user_id: int, workflow_id: int, *, limit: int = 50
    ) -> list[WorkflowRunRead] | None:
        workflow = self._owned(user_id, workflow_id)
        if workflow is None:
            return None
        return [
            self._run_read(r) for r in self._repo.list_runs(workflow.id, limit=limit)
        ]

    # --- Sequence execution ------------------------------------------------

    def _run_sequence(self, workflow: Workflow, run: WorkflowRun) -> None:
        """Walk the workflow's steps, folding each outcome onto the run."""
        steps = self._repo.list_steps(workflow.id) or _legacy_steps(workflow)
        if not steps:
            run.status = WF_RUN_FAILED
            run.error = "Workflow has no steps."
            return

        summaries: list[str] = []
        ok = True
        first_agent_run_id: int | None = None
        for step in steps:
            rstep = self._repo.add_run_step(
                WorkflowRunStep(
                    run_id=run.id,
                    step_index=step.step_index,
                    kind=step.kind,
                    ref=step.ref,
                    status=WF_RUN_RUNNING,
                )
            )
            step_ok, summary, agent_run_id = self._run_step(workflow, step, rstep)
            if agent_run_id is not None and first_agent_run_id is None:
                first_agent_run_id = agent_run_id
            summaries.append(f"{step.ref}: {summary}")
            if not step_ok:
                ok = False
                break  # fail-fast: stop the sequence on the first failure

        run.agent_run_id = first_agent_run_id
        joined = " | ".join(summaries)
        if ok:
            run.status = WF_RUN_COMPLETED
            run.result = joined or None
        else:
            run.status = WF_RUN_FAILED
            run.error = joined or "Workflow step failed."

    def _run_step(
        self, workflow: Workflow, step: WorkflowStep, rstep: WorkflowRunStep
    ) -> tuple[bool, str, int | None]:
        """Run one step, persist its outcome, return (ok, summary, agent_run_id)."""
        ok = True
        summary = ""
        agent_run_id: int | None = None
        try:
            if step.kind == STEP_AGENT:
                ok, summary, agent_run_id = self._run_agent_step(workflow, step, rstep)
            elif step.kind == STEP_TOOL:
                ok, summary = self._run_tool_step(step, rstep)
            else:
                ok, summary = False, f"Unknown step kind '{step.kind}'"
                rstep.status, rstep.error = WF_RUN_FAILED, summary
        except Exception as exc:  # noqa: BLE001 — a step must never crash the run
            ok, summary = False, f"{type(exc).__name__}: {exc}"
            rstep.status, rstep.error = WF_RUN_FAILED, summary

        rstep.finished_at = datetime.now(UTC)
        self._repo.update_run_step(rstep)
        return ok, summary, agent_run_id

    def _run_agent_step(
        self, workflow: Workflow, step: WorkflowStep, rstep: WorkflowRunStep
    ) -> tuple[bool, str, int | None]:
        agent_run = self._agents.start(workflow.user_id, step.ref, step.params or {})
        if agent_run is None:
            rstep.status = WF_RUN_FAILED
            rstep.error = f"Unknown agent '{step.ref}'"
            return False, rstep.error, None

        rstep.agent_run_id = agent_run.id
        if agent_run.status == WF_RUN_COMPLETED:
            rstep.status = WF_RUN_COMPLETED
            rstep.result = agent_run.result
            return True, agent_run.result or "done", agent_run.id
        rstep.status = WF_RUN_FAILED
        rstep.error = agent_run.error or "Agent run failed"
        return False, rstep.error, agent_run.id

    def _run_tool_step(
        self, step: WorkflowStep, rstep: WorkflowRunStep
    ) -> tuple[bool, str]:
        result = self._tools.execute(step.ref, step.params or {})
        if result.startswith(_TOOL_ERROR_PREFIXES):
            rstep.status = WF_RUN_FAILED
            rstep.error = result
            return False, result
        rstep.status = WF_RUN_COMPLETED
        rstep.result = result
        return True, result

    def _record_execution(self, workflow: Workflow) -> None:
        """Bump the run tally and auto-disable once the cap is reached."""
        workflow.run_count += 1
        workflow.last_run_at = datetime.now(UTC)
        if workflow.max_runs is not None and workflow.run_count >= workflow.max_runs:
            workflow.enabled = False
            if self._scheduler is not None:
                self._scheduler.remove(workflow.id)
        self._repo.update(workflow)

    # --- Internals ---------------------------------------------------------

    def _owned(self, user_id: int, workflow_id: int) -> Workflow | None:
        workflow = self._repo.get(workflow_id)
        if workflow is None or workflow.user_id != user_id:
            return None
        return workflow

    def _resolve_input_steps(
        self,
        steps: list[WorkflowStepInput],
        agent_key: str | None,
        params: dict | None,
    ) -> list[WorkflowStepInput]:
        """Use the composed steps, or fall back to the legacy agent shortcut."""
        if steps:
            return steps
        if agent_key:
            return [
                WorkflowStepInput(kind=STEP_AGENT, ref=agent_key, params=params or {})
            ]
        return []

    def _validate_steps(self, steps: list[WorkflowStepInput]) -> None:
        if not steps:
            raise WorkflowError("A workflow needs at least one step.")
        agent_keys = {a.key for a in self._agents.list_agents()}
        tool_names = {spec.name for spec in self._tools.specs()}
        for step in steps:
            if step.kind not in _STEP_KINDS:
                raise WorkflowError(f"Unknown step kind '{step.kind}'.")
            if step.kind == STEP_AGENT and step.ref not in agent_keys:
                raise WorkflowError(f"Unknown agent '{step.ref}'.")
            if step.kind == STEP_TOOL and step.ref not in tool_names:
                raise WorkflowError(f"Unknown tool '{step.ref}'.")

    def _normalize_and_validate(self, workflow: Workflow) -> None:
        """Enforce schedule/trigger combinations and clear irrelevant fields."""
        if workflow.schedule_kind not in _VALID_SCHEDULES:
            raise WorkflowError(f"Unknown schedule kind '{workflow.schedule_kind}'.")

        if workflow.schedule_kind == SCHEDULE_INTERVAL:
            if not workflow.interval_minutes:
                raise WorkflowError(
                    "An interval schedule needs interval_minutes (how often to run)."
                )
            workflow.cron_hour = workflow.cron_minute = None
            workflow.event_type = None
        elif workflow.schedule_kind == SCHEDULE_CRON:
            if workflow.cron_hour is None:
                raise WorkflowError(
                    "A daily schedule needs cron_hour (the time of day to run)."
                )
            workflow.cron_minute = workflow.cron_minute or 0
            workflow.interval_minutes = None
            workflow.event_type = None
        elif workflow.schedule_kind == SCHEDULE_EVENT:
            if workflow.event_type not in EVENT_TYPES:
                raise WorkflowError(
                    "An event trigger needs a valid event_type to react to."
                )
            workflow.interval_minutes = None
            workflow.cron_hour = workflow.cron_minute = None
        else:  # manual
            workflow.interval_minutes = None
            workflow.cron_hour = workflow.cron_minute = None
            workflow.event_type = None
            workflow.enabled = False  # nothing to schedule

    def _arm_if_event(self, workflow: Workflow) -> None:
        """Baseline an enabled event workflow's cursor to the current mark.

        This is what stops a freshly enabled trigger from firing against the
        whole existing backlog: it only reacts to data synced afterwards.
        """
        if (
            workflow.schedule_kind == SCHEDULE_EVENT
            and workflow.enabled
            and workflow.event_type
            and self._session is not None
        ):
            workflow.event_cursor = current_mark(
                self._session, workflow.user_id, workflow.event_type
            )
            self._repo.update(workflow)

    def _sync(self, workflow: Workflow) -> None:
        if self._scheduler is not None:
            self._scheduler.sync(workflow)

    # --- Mappers -----------------------------------------------------------

    def _read(self, workflow: Workflow) -> WorkflowRead:
        rows = self._repo.list_steps(workflow.id)
        if not rows and workflow.agent_key:  # legacy single-agent display
            steps = [
                WorkflowStepRead(
                    step_index=0,
                    kind=STEP_AGENT,
                    ref=workflow.agent_key,
                    params=workflow.params,
                )
            ]
        else:
            steps = [
                WorkflowStepRead(
                    step_index=s.step_index, kind=s.kind, ref=s.ref, params=s.params
                )
                for s in rows
            ]
        return WorkflowRead(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            steps=steps,
            schedule_kind=workflow.schedule_kind,
            interval_minutes=workflow.interval_minutes,
            cron_hour=workflow.cron_hour,
            cron_minute=workflow.cron_minute,
            event_type=workflow.event_type,
            max_runs=workflow.max_runs,
            enabled=workflow.enabled,
            run_count=workflow.run_count,
            last_run_at=workflow.last_run_at,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    def _run_read(self, run: WorkflowRun) -> WorkflowRunRead:
        steps = self._repo.list_run_steps(run.id)
        return WorkflowRunRead(
            id=run.id,
            workflow_id=run.workflow_id,
            trigger=run.trigger,
            status=run.status,
            result=run.result,
            error=run.error,
            agent_run_id=run.agent_run_id,
            steps=[_run_step_read(s) for s in steps],
            created_at=run.created_at,
            finished_at=run.finished_at,
        )


# --- Module helpers ----------------------------------------------------------


def _to_step_rows(steps: list[WorkflowStepInput]) -> list[WorkflowStep]:
    return [
        WorkflowStep(kind=s.kind, ref=s.ref, params=s.params) for s in steps
    ]


def _legacy_steps(workflow: Workflow) -> list[WorkflowStep]:
    """A transient one-step sequence for a pre-MF2 single-agent workflow."""
    if not workflow.agent_key:
        return []
    return [
        WorkflowStep(
            workflow_id=workflow.id,
            step_index=0,
            kind=STEP_AGENT,
            ref=workflow.agent_key,
            params=workflow.params,
        )
    ]


def _primary_agent_ref(steps: list[WorkflowStepInput]) -> str:
    """The first agent step's ref (kept on the legacy column for display)."""
    for step in steps:
        if step.kind == STEP_AGENT:
            return step.ref
    return ""


def _tool_params(schema: dict) -> list[CatalogueParam]:
    """Extract a tool's top-level argument names from its JSON schema."""
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required = set(schema.get("required", []) if isinstance(schema, dict) else [])
    return [
        CatalogueParam(
            name=name,
            description=(spec or {}).get("description"),
            required=name in required,
        )
        for name, spec in properties.items()
    ]


def _run_step_read(step: WorkflowRunStep) -> WorkflowRunStepRead:
    return WorkflowRunStepRead(
        id=step.id,
        step_index=step.step_index,
        kind=step.kind,
        ref=step.ref,
        status=step.status,
        result=step.result,
        error=step.error,
        agent_run_id=step.agent_run_id,
    )

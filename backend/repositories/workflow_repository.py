"""Workflow + WorkflowRun data access. No business logic.

Persists workflow definitions (what runs + its schedule personalization) and
each execution's outcome, so the automation layer has a durable definition store
and an audit trail of every scheduled/triggered run.
"""

from sqlmodel import Session, select

from backend.models.workflow import (
    SCHEDULE_EVENT,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStep,
)


class WorkflowRepository:
    """Queries and transactions for workflows and their runs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Workflows ---------------------------------------------------------

    def get(self, workflow_id: int) -> Workflow | None:
        return self._session.get(Workflow, workflow_id)

    def list_for_user(self, user_id: int) -> list[Workflow]:
        statement = (
            select(Workflow)
            .where(Workflow.user_id == user_id)
            .order_by(Workflow.created_at.desc())  # type: ignore[union-attr]
        )
        return list(self._session.exec(statement).all())

    def list_enabled(self) -> list[Workflow]:
        """All enabled workflows across users — used to bootstrap the scheduler."""
        statement = select(Workflow).where(Workflow.enabled == True)  # noqa: E712
        return list(self._session.exec(statement).all())

    def list_enabled_events(self) -> list[Workflow]:
        """All enabled event-triggered workflows — used by the event evaluator."""
        statement = select(Workflow).where(
            Workflow.enabled == True,  # noqa: E712
            Workflow.schedule_kind == SCHEDULE_EVENT,
        )
        return list(self._session.exec(statement).all())

    def add(self, workflow: Workflow) -> Workflow:
        self._session.add(workflow)
        self._session.commit()
        self._session.refresh(workflow)
        return workflow

    def update(self, workflow: Workflow) -> Workflow:
        self._session.add(workflow)
        self._session.commit()
        self._session.refresh(workflow)
        return workflow

    def delete(self, workflow: Workflow) -> None:
        # Drop the steps + run history (and their step rows) with the definition
        # so no orphan rows remain.
        for run in self.list_runs(workflow.id, limit=None):
            for run_step in self.list_run_steps(run.id):
                self._session.delete(run_step)
            self._session.delete(run)
        for step in self.list_steps(workflow.id):
            self._session.delete(step)
        self._session.delete(workflow)
        self._session.commit()

    # --- Steps (the composed sequence) -------------------------------------

    def list_steps(self, workflow_id: int) -> list[WorkflowStep]:
        statement = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .order_by(WorkflowStep.step_index)  # type: ignore[arg-type]
        )
        return list(self._session.exec(statement).all())

    def replace_steps(
        self, workflow_id: int, steps: list[WorkflowStep]
    ) -> list[WorkflowStep]:
        """Swap a workflow's whole sequence for a fresh, re-indexed one."""
        for existing in self.list_steps(workflow_id):
            self._session.delete(existing)
        for index, step in enumerate(steps):
            step.workflow_id = workflow_id
            step.step_index = index
            self._session.add(step)
        self._session.commit()
        return self.list_steps(workflow_id)

    # --- Runs --------------------------------------------------------------

    def add_run(self, run: WorkflowRun) -> WorkflowRun:
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    def update_run(self, run: WorkflowRun) -> WorkflowRun:
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    def list_runs(
        self, workflow_id: int, *, limit: int | None = 50
    ) -> list[WorkflowRun]:
        statement = (
            select(WorkflowRun)
            .where(WorkflowRun.workflow_id == workflow_id)
            .order_by(WorkflowRun.created_at.desc())  # type: ignore[union-attr]
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self._session.exec(statement).all())

    # --- Run steps (the step-visibility trail) -----------------------------

    def add_run_step(self, run_step: WorkflowRunStep) -> WorkflowRunStep:
        self._session.add(run_step)
        self._session.commit()
        self._session.refresh(run_step)
        return run_step

    def update_run_step(self, run_step: WorkflowRunStep) -> WorkflowRunStep:
        self._session.add(run_step)
        self._session.commit()
        self._session.refresh(run_step)
        return run_step

    def list_run_steps(self, run_id: int) -> list[WorkflowRunStep]:
        statement = (
            select(WorkflowRunStep)
            .where(WorkflowRunStep.run_id == run_id)
            .order_by(WorkflowRunStep.step_index)  # type: ignore[arg-type]
        )
        return list(self._session.exec(statement).all())

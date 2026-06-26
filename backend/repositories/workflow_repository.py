"""Workflow + WorkflowRun data access. No business logic.

Persists workflow definitions (what runs + its schedule personalization) and
each execution's outcome, so the automation layer has a durable definition store
and an audit trail of every scheduled/triggered run.
"""

from sqlmodel import Session, select

from backend.models.workflow import Workflow, WorkflowRun


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
        # Drop the run history with the definition so no orphan rows remain.
        for run in self.list_runs(workflow.id, limit=None):
            self._session.delete(run)
        self._session.delete(workflow)
        self._session.commit()

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

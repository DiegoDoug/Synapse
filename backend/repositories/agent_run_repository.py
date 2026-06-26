"""AgentRun + AgentStep data access. No business logic.

Persists agent runs and their plan→act→observe steps so a run's reasoning and
any destructive action it routed through the confirmation flow remain auditable
after the fact.
"""

from sqlmodel import Session, select

from backend.models.agent_run import AgentRun, AgentStep


class AgentRunRepository:
    """Queries and transactions for agent runs and their steps."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Runs --------------------------------------------------------------

    def get(self, run_id: int) -> AgentRun | None:
        return self._session.get(AgentRun, run_id)

    def list_for_user(
        self, user_id: int, *, limit: int = 50, offset: int = 0
    ) -> list[AgentRun]:
        statement = (
            select(AgentRun)
            .where(AgentRun.user_id == user_id)
            .order_by(AgentRun.created_at.desc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def add_run(self, run: AgentRun) -> AgentRun:
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    def update_run(self, run: AgentRun) -> AgentRun:
        self._session.add(run)
        self._session.commit()
        self._session.refresh(run)
        return run

    # --- Steps -------------------------------------------------------------

    def add_step(self, step: AgentStep) -> AgentStep:
        self._session.add(step)
        self._session.commit()
        self._session.refresh(step)
        return step

    def list_steps(self, run_id: int) -> list[AgentStep]:
        statement = (
            select(AgentStep)
            .where(AgentStep.run_id == run_id)
            .order_by(AgentStep.step_index)  # type: ignore[arg-type]
        )
        return list(self._session.exec(statement).all())

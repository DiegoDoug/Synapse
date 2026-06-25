"""System prompt data access. No business logic."""

from sqlmodel import Session, select

from backend.models.system_prompt import SystemPrompt


class SystemPromptRepository:
    """Queries and transactions for selectable system prompts."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, prompt_id: int) -> SystemPrompt | None:
        return self._session.get(SystemPrompt, prompt_id)

    def get_by_name(self, name: str) -> SystemPrompt | None:
        statement = select(SystemPrompt).where(SystemPrompt.name == name)
        return self._session.exec(statement).first()

    def list(self) -> list[SystemPrompt]:
        statement = select(SystemPrompt).order_by(SystemPrompt.name.asc())  # type: ignore[union-attr]
        return list(self._session.exec(statement).all())

    def add(self, prompt: SystemPrompt) -> SystemPrompt:
        self._session.add(prompt)
        self._session.commit()
        self._session.refresh(prompt)
        return prompt

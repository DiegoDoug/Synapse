"""SyncState data access. No business logic."""

from sqlmodel import Session, select

from backend.models.sync_state import SyncState


class SyncStateRepository:
    """Queries and transactions for per-resource sync checkpoints."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, account_id: int, resource: str) -> SyncState | None:
        statement = select(SyncState).where(
            SyncState.account_id == account_id, SyncState.resource == resource
        )
        return self._session.exec(statement).first()

    def list_for_account(self, account_id: int) -> list[SyncState]:
        statement = select(SyncState).where(SyncState.account_id == account_id)
        return list(self._session.exec(statement).all())

    def upsert(self, state: SyncState) -> SyncState:
        self._session.add(state)
        self._session.commit()
        self._session.refresh(state)
        return state

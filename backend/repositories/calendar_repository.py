"""CalendarEvent data access. No business logic."""

from sqlmodel import Session, select

from backend.models.calendar_event import CalendarEvent


class CalendarRepository:
    """Queries and transactions for synced calendar events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, event_id: int) -> CalendarEvent | None:
        return self._session.get(CalendarEvent, event_id)

    def get_by_external_id(self, account_id: int, external_id: str) -> CalendarEvent | None:
        statement = select(CalendarEvent).where(
            CalendarEvent.account_id == account_id,
            CalendarEvent.external_id == external_id,
        )
        return self._session.exec(statement).first()

    def list_for_account(
        self,
        account_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CalendarEvent]:
        statement = (
            select(CalendarEvent)
            .where(CalendarEvent.account_id == account_id)
            .order_by(CalendarEvent.start.asc())  # type: ignore[union-attr]
            .offset(offset)
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def upsert(self, event: CalendarEvent) -> CalendarEvent:
        self._session.add(event)
        self._session.commit()
        self._session.refresh(event)
        return event

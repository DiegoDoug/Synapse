"""Dashboard widget data access. No business logic."""

from sqlmodel import Session, select

from backend.models.dashboard_widget import DashboardWidget


class WidgetRepository:
    """Queries and transactions for dashboard widgets."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, widget_id: int) -> DashboardWidget | None:
        return self._session.get(DashboardWidget, widget_id)

    def list_for_user(self, user_id: int) -> list[DashboardWidget]:
        statement = (
            select(DashboardWidget)
            .where(DashboardWidget.user_id == user_id)
            .order_by(DashboardWidget.position.asc())  # type: ignore[union-attr]
        )
        return list(self._session.exec(statement).all())

    def add(self, widget: DashboardWidget) -> DashboardWidget:
        self._session.add(widget)
        self._session.commit()
        self._session.refresh(widget)
        return widget

    def update(self, widget: DashboardWidget) -> DashboardWidget:
        self._session.add(widget)
        self._session.commit()
        self._session.refresh(widget)
        return widget

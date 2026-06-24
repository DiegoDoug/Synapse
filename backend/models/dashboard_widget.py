"""DashboardWidget model (SQLModel). Schema only — no business logic."""

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class DashboardWidget(SQLModel, table=True):
    """A widget displayed on the dashboard."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="user.id", index=True)
    widget_type: str
    title: str
    position: int = Field(default=0)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

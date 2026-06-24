"""SQLModel table definitions (data layer).

Importing the models here registers them on SQLModel.metadata so that
create_all() can build their tables.
"""

from backend.models.account import Account
from backend.models.calendar_event import CalendarEvent
from backend.models.dashboard_widget import DashboardWidget
from backend.models.email_message import EmailMessage
from backend.models.sync_state import SyncState
from backend.models.user import User

__all__ = [
    "Account",
    "CalendarEvent",
    "DashboardWidget",
    "EmailMessage",
    "SyncState",
    "User",
]

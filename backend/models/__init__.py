"""SQLModel table definitions (data layer).

Importing the models here registers them on SQLModel.metadata so that
create_all() can build their tables.
"""

from backend.models.dashboard_widget import DashboardWidget
from backend.models.user import User

__all__ = ["DashboardWidget", "User"]

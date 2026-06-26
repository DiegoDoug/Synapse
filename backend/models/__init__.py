"""SQLModel table definitions (data layer).

Importing the models here registers them on SQLModel.metadata so that
create_all() can build their tables.
"""

from backend.models.account import Account
from backend.models.agent_run import AgentRun, AgentStep
from backend.models.calendar_event import CalendarEvent
from backend.models.conversation import Conversation
from backend.models.dashboard_widget import DashboardWidget
from backend.models.document import Document, DocumentChunk
from backend.models.email_message import EmailMessage
from backend.models.message import Message
from backend.models.notification import Notification
from backend.models.pending_action import PendingAction
from backend.models.sync_state import SyncState
from backend.models.system_prompt import SystemPrompt
from backend.models.task import Task
from backend.models.user import User
from backend.models.workflow import Workflow, WorkflowRun

__all__ = [
    "Account",
    "AgentRun",
    "AgentStep",
    "CalendarEvent",
    "Conversation",
    "DashboardWidget",
    "Document",
    "DocumentChunk",
    "EmailMessage",
    "Message",
    "Notification",
    "PendingAction",
    "SyncState",
    "SystemPrompt",
    "Task",
    "User",
    "Workflow",
    "WorkflowRun",
]

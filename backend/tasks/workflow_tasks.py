"""Scheduled workflow job callable.

Thin orchestration only: open a session, build the ``WorkflowService`` via the
factory, and execute the due workflow. No automation logic lives here — the
service drives the Stage 6 agent layer. The job is best-effort so a single
failure never tears down the scheduler.
"""

import logging

from sqlmodel import Session

from backend.config import get_settings
from backend.database import engine
from backend.models.workflow import TRIGGER_SCHEDULE
from backend.services.factory import build_workflow_service, owner_user_id

logger = logging.getLogger(__name__)


def run_scheduled_workflow(workflow_id: int) -> None:
    """Execute one workflow on a scheduler tick (best-effort)."""
    settings = get_settings()
    try:
        with Session(engine) as session:
            user_id = owner_user_id(session)
            if user_id is None:
                return
            service = build_workflow_service(session, settings, user_id)
            workflow = service.execute_by_id(workflow_id, trigger=TRIGGER_SCHEDULE)
            if workflow is None:
                logger.warning("Scheduled workflow %s no longer exists.", workflow_id)
    except Exception:  # noqa: BLE001 — never let a job crash the scheduler
        logger.exception("Scheduled workflow %s failed.", workflow_id)


def evaluate_workflow_events() -> None:
    """Fire event-triggered workflows whose synced data changed (best-effort)."""
    settings = get_settings()
    try:
        with Session(engine) as session:
            user_id = owner_user_id(session)
            if user_id is None:
                return
            build_workflow_service(session, settings, user_id).evaluate_events()
    except Exception:  # noqa: BLE001 — never let a job crash the scheduler
        logger.exception("Workflow event evaluation failed.")

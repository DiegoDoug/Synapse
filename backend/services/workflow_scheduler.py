"""WorkflowScheduler — turns a workflow's schedule definition into live jobs.

A thin adapter over the Stage 3 APScheduler instance. It only *registers and
removes jobs* — it owns no automation logic; the job it schedules opens its own
session and drives the ``WorkflowService`` (which reuses the Stage 6 agent
layer). One job per workflow, keyed by id, so a definition change re-syncs in
place.

A process-level singleton (``set/get_workflow_scheduler``) lets request handlers
sync jobs when a workflow changes while the scheduler runs in the app lifespan.
When scheduling is disabled (e.g. in tests) the singleton is ``None`` and the
service degrades gracefully: it still persists definitions and runs on demand.
"""

from __future__ import annotations

import logging

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.models.workflow import (
    SCHEDULE_CRON,
    SCHEDULE_INTERVAL,
    Workflow,
)

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """Register/remove one APScheduler job per enabled, timed workflow."""

    def __init__(self, scheduler: BaseScheduler) -> None:
        self._scheduler = scheduler

    @staticmethod
    def job_id(workflow_id: int) -> str:
        return f"workflow-{workflow_id}"

    def sync(self, workflow: Workflow) -> None:
        """Make the live job match the workflow's current schedule.

        Removes the existing job first, then (re)adds it only when the workflow
        is enabled and has a timed schedule. A manual or disabled workflow ends
        up with no job.
        """
        self.remove(workflow.id)
        trigger = _build_trigger(workflow)
        if not workflow.enabled or trigger is None:
            return

        # Imported lazily to avoid an import cycle: the task module builds the
        # service via the factory, which imports this module.
        from backend.tasks.workflow_tasks import run_scheduled_workflow

        self._scheduler.add_job(
            run_scheduled_workflow,
            trigger,
            args=[workflow.id],
            id=self.job_id(workflow.id),
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        logger.info("Scheduled workflow %s (%s).", workflow.id, workflow.name)

    def remove(self, workflow_id: int) -> None:
        try:
            self._scheduler.remove_job(self.job_id(workflow_id))
        except JobLookupError:
            pass  # No live job — nothing to remove.


def _build_trigger(
    workflow: Workflow,
) -> IntervalTrigger | CronTrigger | None:
    """Translate a workflow's schedule fields into an APScheduler trigger."""
    if workflow.schedule_kind == SCHEDULE_INTERVAL and workflow.interval_minutes:
        return IntervalTrigger(minutes=workflow.interval_minutes)
    if workflow.schedule_kind == SCHEDULE_CRON and workflow.cron_hour is not None:
        return CronTrigger(
            hour=workflow.cron_hour, minute=workflow.cron_minute or 0
        )
    return None


# --- Process singleton -------------------------------------------------------

_instance: WorkflowScheduler | None = None


def set_workflow_scheduler(scheduler: WorkflowScheduler | None) -> None:
    """Publish the active scheduler (called once from the app lifespan)."""
    global _instance
    _instance = scheduler


def get_workflow_scheduler() -> WorkflowScheduler | None:
    """Return the active scheduler, or None when scheduling is disabled."""
    return _instance

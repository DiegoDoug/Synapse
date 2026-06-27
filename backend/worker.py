"""Standalone automation worker (Stage 8 — production process split).

In production the scheduler runs as its own container instead of inside the API
process, so the API stays stateless and horizontally scalable while exactly one
worker owns the cron/interval jobs (notifications, Telegram polling, Stage 7
workflows + event triggers). It reuses ``create_scheduler`` unchanged — same
jobs, same services — and simply keeps the process alive.

Run with: ``python -m backend.worker``.
Set ``SCHEDULER_ENABLED=false`` on the API container so jobs are not scheduled
twice; keep it ``true`` here (the default).
"""

from __future__ import annotations

import logging
import signal
import threading

from backend.config import get_settings
from backend.database import create_db_and_tables
from backend.logging_config import configure_logging
from backend.scheduler import create_scheduler

settings = get_settings()
configure_logging(log_format=settings.log_format, level=settings.log_level)
logger = logging.getLogger(__name__)


def main() -> None:
    """Boot the scheduler and block until a termination signal arrives."""
    create_db_and_tables()
    scheduler = create_scheduler(settings)
    if scheduler is None:
        logger.warning("SCHEDULER_ENABLED is false; worker has nothing to do. Exiting.")
        return

    scheduler.start()
    logger.info("Automation worker started.", extra={"environment": settings.environment})

    stop = threading.Event()

    def _shutdown(signum, _frame) -> None:
        logger.info("Received signal %s; shutting down worker.", signum)
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        stop.wait()
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Automation worker stopped.")


if __name__ == "__main__":
    main()

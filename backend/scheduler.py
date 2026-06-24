"""APScheduler wiring (Stage 3).

Builds the background scheduler and registers notification jobs. The scheduler
only *triggers* service methods — no notification logic lives here. Started and
stopped by the FastAPI lifespan in main.py.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from backend.config import Settings
from backend.database import engine
from backend.services.factory import build_telegram_integration
from backend.services.telegram_service import TelegramService
from backend.tasks.notification_tasks import poll_and_deliver, send_daily_summary

logger = logging.getLogger(__name__)


def create_scheduler(settings: Settings) -> BackgroundScheduler | None:
    """Build a configured scheduler, or None when scheduling is disabled."""
    if not settings.scheduler_enabled:
        return None

    scheduler = BackgroundScheduler(timezone="UTC")

    scheduler.add_job(
        poll_and_deliver,
        "interval",
        minutes=settings.notification_poll_minutes,
        args=[settings],
        id="notification-poll",
        replace_existing=True,
    )
    scheduler.add_job(
        send_daily_summary,
        "cron",
        hour=settings.daily_summary_hour,
        minute=0,
        args=[settings],
        id="daily-summary",
        replace_existing=True,
    )

    # Inbound command polling only runs when a bot is configured. A single
    # long-lived TelegramService keeps the update offset across polls.
    telegram = build_telegram_integration(settings)
    if telegram is not None:
        commands = TelegramService(telegram, lambda: Session(engine), settings)
        scheduler.add_job(
            commands.poll,
            "interval",
            minutes=1,
            id="telegram-commands",
            replace_existing=True,
        )
        logger.info("Telegram command polling enabled.")

    return scheduler

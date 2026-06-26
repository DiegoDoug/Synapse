"""FastAPI application entrypoint.

Builds the app, configures CORS, creates database tables on startup, and
mounts the versioned API router. No business logic.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import api_router
from backend.config import get_settings
from backend.database import create_db_and_tables
from backend.scheduler import create_scheduler
from backend.services.workflow_scheduler import set_workflow_scheduler

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables and run the notification scheduler."""
    create_db_and_tables()
    scheduler = create_scheduler(settings)
    if scheduler is not None:
        scheduler.start()
        logger.info("Notification scheduler started.")
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)
        set_workflow_scheduler(None)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

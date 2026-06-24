"""API route handlers (endpoints).

Aggregates feature routers into a single api_router mounted by main.py.
"""

from fastapi import APIRouter

from backend.api.routes.calendar import router as calendar_router
from backend.api.routes.connections import router as connections_router
from backend.api.routes.email import router as email_router
from backend.api.routes.health import router as health_router
from backend.api.routes.notifications import router as notifications_router
from backend.api.routes.sync import router as sync_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(connections_router)
api_router.include_router(email_router)
api_router.include_router(calendar_router)
api_router.include_router(sync_router)
api_router.include_router(notifications_router)

__all__ = ["api_router"]

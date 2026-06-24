"""API route handlers (endpoints).

Aggregates feature routers into a single api_router mounted by main.py.
"""

from fastapi import APIRouter

from backend.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)

__all__ = ["api_router"]

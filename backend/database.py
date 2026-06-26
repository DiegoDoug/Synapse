"""Database engine and session management.

SQLite + SQLModel engine, table creation, and a session dependency.
No business logic.
"""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from backend.config import get_settings

settings = get_settings()


def _build_engine():
    """Create the SQLModel engine, adapting options to the DB driver.

    SQLite needs ``check_same_thread=False`` under FastAPI's threadpool and does
    not support a connection pool. PostgreSQL (Stage 8 production) uses a real
    pool sized from settings, with ``pool_pre_ping`` so stale connections are
    detected and recycled rather than surfacing as errors.
    """
    url = settings.database_url
    if url.startswith("sqlite"):
        return create_engine(
            url,
            echo=settings.debug,
            connect_args={"check_same_thread": False},
        )
    return create_engine(
        url,
        echo=settings.debug,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
    )


engine = _build_engine()


def create_db_and_tables() -> None:
    """Create the SQLite file (and parent dir) and all SQLModel tables."""
    # Import models so they register on SQLModel.metadata before create_all.
    from backend import models  # noqa: F401

    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a database session (FastAPI dependency)."""
    with Session(engine) as session:
        yield session

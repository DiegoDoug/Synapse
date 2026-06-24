"""Database engine and session management.

SQLite + SQLModel engine, table creation, and a session dependency.
No business logic.
"""

from collections.abc import Generator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from backend.config import get_settings

settings = get_settings()

# check_same_thread=False is required for SQLite under FastAPI's threadpool.
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)


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

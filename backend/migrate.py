"""Migration runner (Stage 8 — production startup migrations).

The schema is defined declaratively with SQLModel, so "migration" here means
``create_all`` (idempotent: it only creates missing tables/indexes). This module
adds two production concerns on top:

  * **Locking safety** — on PostgreSQL it takes a transaction-level advisory
    lock before creating tables, so when several containers (api, worker) start
    at once exactly one runs the DDL and the others wait, avoiding races.
  * **A single entrypoint** — ``python -m backend.migrate`` is what the deploy
    scripts and container startup call before serving traffic.

SQLite simply runs ``create_all`` (no advisory locks; single-writer anyway).
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from backend.config import get_settings
from backend.database import create_db_and_tables, engine
from backend.logging_config import configure_logging

logger = logging.getLogger(__name__)

# Arbitrary but stable 64-bit key for the Postgres advisory lock namespace.
_ADVISORY_LOCK_KEY = 873214567


def run_migrations() -> None:
    """Create/upgrade the schema, serializing concurrent runners on Postgres."""
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        logger.info("Running SQLite schema sync (create_all).")
        create_db_and_tables()
        return

    logger.info("Acquiring migration advisory lock.")
    with engine.begin() as conn:
        # Transaction-scoped lock: auto-released on commit. Blocks peers until
        # this connection's DDL transaction finishes.
        conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})
        logger.info("Lock acquired; applying schema (create_all).")
        # Import models so metadata is populated, then create within this txn.
        from sqlmodel import SQLModel

        from backend import models  # noqa: F401

        SQLModel.metadata.create_all(conn)
    logger.info("Migrations complete.")


def main() -> None:
    settings = get_settings()
    configure_logging(log_format=settings.log_format, level=settings.log_level)
    run_migrations()


if __name__ == "__main__":
    main()

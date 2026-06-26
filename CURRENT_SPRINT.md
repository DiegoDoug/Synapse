# Current Sprint

Current Stage: Stage 8

Objective:

Make Personal OS **production-ready**: replace SQLite with PostgreSQL, add Redis
for caching and task queuing, containerize the full stack with Docker Compose,
and establish horizontal-scaling fundamentals. This stage is infrastructure and
deployment only — no new features, no new integrations, no changes to the AI or
automation layers built in Stages 1–7.

---

# Allowed Features

Backend:

- replace SQLite (`data/synapse.db`) with **PostgreSQL** via SQLModel / asyncpg
- replace in-process APScheduler + workflow task functions with **Celery** workers
  backed by Redis as broker and result backend
- **Redis** cache layer: short-lived caches for catalogue, agent responses, and
  read-heavy queries
- Docker Compose service definitions: `api`, `worker`, `frontend`, `db`
  (PostgreSQL), `cache` (Redis)
- Alembic migration baseline from the Stage 7 schema
- environment-variable–driven config (`DATABASE_URL`, `REDIS_URL`, etc.) via
  `backend/config.py`
- production-grade logging (structured JSON, log level from env)
- health-check endpoints (`/healthz`, `/readyz`) suitable for container
  orchestrators

Frontend:

- Nginx reverse-proxy container serving the Vite production build
- environment-variable injection (`VITE_API_URL`) via Docker Compose

---

# Architecture Contract

- **No new features** — the API surface, data models, and AI/automation contracts
  from Stages 1–7 are frozen for this stage.
- **SQLModel stays** — only the engine/session configuration changes
  (SQLite → PostgreSQL); all model definitions and repository methods remain.
- **Celery replaces in-process tasks** — `run_scheduled_workflow` and
  `evaluate_workflow_events` move to Celery tasks; APScheduler still schedules
  them but dispatches to the Celery queue instead of calling functions directly.
- **Backward compatibility** — the Alembic baseline migration must produce
  a schema identical to `SQLModel.metadata.create_all` output from Stage 7.

---

# Restrictions

DO NOT implement:

- new external integrations beyond what Stages 2–4.5 already provide
- changes to the AI chat, agent, or automation logic
- multi-user / multi-tenant support — future stage
- Kubernetes / cloud deployment — out of scope for this stage
- new frontend pages or UI components (Nginx config only)

Do not implement future stages beyond Stage 8.

---

# Deliverables

- `docker-compose.yml` — api, worker, frontend, db, cache services
- `Dockerfile` (backend) — production FastAPI image
- `frontend/Dockerfile` — Nginx image serving Vite build
- `alembic/` — migration environment + baseline migration from Stage 7 schema
- `backend/config.py` — updated with `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`
- `backend/db.py` — PostgreSQL engine + session factory (replaces SQLite setup)
- `backend/tasks/celery_app.py` — Celery application instance
- `backend/tasks/workflow_tasks.py` — migrated to Celery tasks
- `backend/api/routes/health.py` — `/healthz` and `/readyz` endpoints
- `.env.example` — all required environment variables with safe defaults
- updated `README.md` — local dev with Docker Compose instructions

---

# Development Process

Build incrementally:

Step 1: PostgreSQL + Alembic baseline
- swap SQLite engine for PostgreSQL
- create Alembic environment and generate baseline migration
- verify all 150+ existing tests pass against PostgreSQL (use test DB)

Step 2: Redis + Celery task queue
- add Celery app; move `run_scheduled_workflow` and `evaluate_workflow_events`
  to Celery tasks; APScheduler dispatches to queue
- add Redis cache helper; apply to catalogue and read-heavy endpoints
- verify scheduler + automation tests pass

Step 3: Docker Compose + production images
- write Dockerfiles for backend and frontend (Nginx)
- write `docker-compose.yml` with health checks and dependency ordering
- verify `docker compose up` starts a fully functional stack

Step 4: Health endpoints + config + docs
- add `/healthz` (liveness) and `/readyz` (readiness: DB + Redis reachable)
- finalize `.env.example`; update README with compose instructions
- run full test suite; confirm clean build

After each step:

- explain decisions
- list files created / modified
- wait for approval

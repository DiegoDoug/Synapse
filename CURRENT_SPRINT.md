# Current Sprint

Current Stage: Stage 8

Objective:

Transform Personal OS from a working prototype into a **production-ready,
deployable system**. Stage 8 is **infrastructure and operations**, not feature
work: it adds production Docker, CI/CD, environment management, database
hardening (PostgreSQL), a reverse proxy with TLS, observability, security
hardening, and deployment automation — all **additive** and **backward
compatible**. No application API, folder structure, or core architecture is
refactored.

This builds directly on the Stages 1–7 modular monolith (FastAPI + SQLModel
backend, React/Vite frontend, APScheduler automation) and the
ARCHITECTURE.md layering, which remain unchanged at runtime.

---

# Allowed Features

Infrastructure / operations only:

- **Production Docker**: multi-stage backend/frontend images +
  `docker-compose.prod.yml` (backend, frontend, postgres, redis, worker, proxy)
  with health checks, restart policies, resource limits, network isolation
- **Environment management**: documented `.env.example` + tracked
  `.env.production` / `.env.staging` templates (public config only), central
  config loader with fail-fast production validation
- **Database hardening**: PostgreSQL with persistent volumes, connection
  pooling, a locked migration runner at startup, and a backup script
- **CI/CD**: GitHub Actions — lint, test, dependency security scan, image build,
  push to registry, deploy (staging automatic, production manual approval)
- **Reverse proxy + TLS**: nginx with HTTP→HTTPS redirect, `/api`→backend,
  `/`→frontend, Let's Encrypt (self-signed fallback)
- **Observability**: structured JSON logging, Prometheus `/metrics`, request-id
  propagation middleware (lightweight tracing)
- **Security hardening**: rate limiting, strict CORS, security headers, secrets
  kept out of the repo, secure-cookie + token-expiry settings
- **Deployment automation**: `deploy-prod.sh`, `deploy-staging.sh`,
  `rollback.sh`, with post-deploy health checks and auto-rollback
- **Documentation**: `DEPLOYMENT.md`

---

# Architecture Contract

- **Additive only** — no change to application APIs, the
  Agent→Service→Integration contract, the folder structure, or business logic.
- **Stateless API, single worker** — the FastAPI container runs stateless with
  the scheduler disabled; exactly one `worker` container owns the cron/interval
  and Stage 7 workflow jobs (reusing `create_scheduler` unchanged).
- **Config over code** — all production behavior is environment-driven via
  `backend/config.py`; defaults keep dev/test running with zero configuration.
- **Graceful degradation** — optional production deps (prometheus-client, redis)
  are imported lazily; the app boots and serves without them.
- **Fail fast in production** — the app refuses to start on an insecure prod
  config (debug on, wildcard CORS, SQLite, missing AI key).

---

# Restrictions

DO NOT implement:

- new product features or integrations beyond Stages 1–7
- changes to the Stage 4.5 confirmation flow, the Stage 5 retrieval core, the
  Stage 6 agent contract, or the Stage 7 automation semantics
- horizontal multi-node orchestration (Kubernetes) — single-node compose target
- refactors of the core architecture or folder layout

Do not implement future stages beyond Stage 8.

---

# Deliverables

- production Docker architecture (`docker-compose.prod.yml`, multi-stage images)
- environment management system (`.env.example` + prod/staging templates +
  validated config loader)
- PostgreSQL hardening (pooling, locked migrations, backup/restore scripts)
- CI/CD pipelines (`.github/workflows/ci.yml`, `deploy.yml`)
- nginx reverse proxy + TLS (`nginx/`, self-signed cert script)
- observability (JSON logs, `/metrics`, request-id middleware)
- security hardening (rate limiting, CORS, security headers, secret hygiene)
- deployment automation (`scripts/deploy-*.sh`, `rollback.sh`, `backup-db.sh`)
- `DEPLOYMENT.md`

---

# Success Criteria

Stage 8 is complete only when:

- the entire system boots from zero via `docker-compose.prod.yml`
- the API is reachable behind the reverse proxy over TLS
- the database persists across restarts
- the CI pipeline runs green (lint, tests, security scan, image build)
- logs are structured and metrics are exposed
- rate limiting and the security baseline are enforced in production
- deployment is repeatable, automated, and auto-rolls-back on failed health

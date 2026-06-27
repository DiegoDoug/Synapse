# Deployment Guide — Synapse / Personal OS

Stage 8 production operations manual: how to build, configure, deploy, observe,
and roll back the system. This document is the single source of truth for
running Synapse in staging and production.

> **Architecture note (Stage 8 constraint):** Stage 8 is **additive**. The
> application code, folder structure, and APIs are unchanged. Everything here
> layers production concerns (containers, TLS, observability, security, CI/CD)
> on top of the existing modular monolith.

---

## 1. Topology

```
                        Internet
                           │  (80/443)
                    ┌──────▼───────┐
                    │    proxy     │  nginx — TLS termination, HTTP→HTTPS
                    │  (reverse)   │  /api → backend   / → frontend
                    └──┬────────┬──┘
              edge net │        │ edge net
                ┌──────▼──┐  ┌──▼────────┐
                │ frontend │  │  backend  │  FastAPI (uvicorn, stateless)
                │ (static) │  │  :8000    │  SCHEDULER_ENABLED=false
                └──────────┘  └──┬─────┬──┘
                                 │     │ internal net (no host ports)
                          ┌──────▼─┐ ┌─▼──────┐
                          │postgres│ │ redis  │
                          └────▲───┘ └────▲───┘
                               │ internal │
                          ┌────┴──────────┴───┐
                          │      worker        │  scheduler/automation
                          │ SCHEDULER_ENABLED= │  (cron, workflows, events)
                          │       true         │
                          └────────────────────┘
```

| Service    | Image                         | Public | Purpose |
|------------|-------------------------------|:------:|---------|
| `proxy`    | `nginx:1.27-alpine`           |  ✅ 80/443 | TLS, routing, HSTS |
| `frontend` | `…/frontend` (multi-stage)    |  —     | Static SPA |
| `backend`  | `…/backend` (multi-stage)     |  —     | API (stateless, 2 workers) |
| `worker`   | `…/backend` (same image)      |  —     | Scheduler + automation |
| `postgres` | `postgres:16-alpine`          |  —     | Primary database |
| `redis`    | `redis:7-alpine`              |  —     | Cache + rate-limit backend |

Networks: **`edge`** (proxy ↔ frontend/backend) and **`internal`**
(`internal: true`, no host exposure) for backend/worker ↔ postgres/redis.

---

## 2. Prerequisites

- Docker Engine 24+ and Docker Compose v2
- A domain pointing at the host (for Let's Encrypt) — optional for local
- Outbound access to the container registry (GHCR by default)

---

## 3. Environment configuration

Configuration is environment-variable driven (`backend/config.py:Settings`).
Three layers of env files:

| File              | Tracked? | Use |
|-------------------|:--------:|-----|
| `.env.example`    | ✅ | Documented template of **every** variable |
| `.env.staging`    | ✅ | Staging **public** config + empty secret placeholders |
| `.env.production` | ✅ | Production **public** config + empty secret placeholders |
| `.env.*.local`    | ❌ | Operator-local real secrets (git-ignored) |

**Secrets are never committed.** The tracked `.env.production` /`.env.staging`
files contain only public config and empty placeholders. Supply real secret
values one of these ways at deploy time:

1. **CI/CD secret store** (recommended) — the Deploy workflow injects them.
2. **Server-local overlay** — put real values in `.env.production.local` on the
   host and `export $(grep -v '^#' .env.production.local | xargs)` before
   deploying, or merge into the env file out-of-band.
3. **Orchestrator secrets** — Docker/K8s secrets mounted at runtime.

### Fail-fast validation

On startup the backend calls `Settings.validate_runtime()`. In **production**
the app refuses to boot if:

- `DEBUG=true`
- `CORS_ORIGINS` is empty or contains `*`
- `DATABASE_URL` still points at SQLite
- the selected AI provider's API key is missing (non-Ollama)

Staging warns but still boots. This is the "zero manual configuration after
initial setup" guard — a misconfigured prod deploy stops immediately.

### Required production secrets

| Variable | Notes |
|----------|-------|
| `POSTGRES_PASSWORD` | DB password (also referenced by `DATABASE_URL`) |
| `ANTHROPIC_API_KEY` (or provider key) | AI layer |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Gmail/Calendar OAuth |
| `TELEGRAM_BOT_TOKEN` | Optional — notification delivery |

---

## 4. TLS / certificates

The proxy expects `nginx/certs/fullchain.pem` and `nginx/certs/privkey.pem`.

**Local / staging fallback (self-signed):**

```bash
./scripts/generate-self-signed-cert.sh your-domain.com
```

**Production (Let's Encrypt, preferred):** issue certs with certbot using the
HTTP-01 webroot the proxy already serves at `/.well-known/acme-challenge/`
(mounted from the `certbot-webroot` volume), then point
`nginx/certs/fullchain.pem` / `privkey.pem` at the issued files (symlink or
copy) and reload the proxy:

```bash
docker compose -f docker-compose.prod.yml exec proxy nginx -s reload
```

Certificates and keys are git-ignored (`nginx/certs/*.pem|*.key|*.crt`).

---

## 5. First deploy (from zero)

```bash
# 1. Clone + check out the release
git clone <repo> && cd Synapse

# 2. Provide secrets (see §3) — e.g. edit a local overlay
cp .env.production .env.production.local   # then fill in secrets

# 3. TLS material
./scripts/generate-self-signed-cert.sh app.example.com   # or install LE certs

# 4. Bring the whole stack up
export REGISTRY=ghcr.io/<owner>/<repo> IMAGE_TAG=latest
./scripts/deploy-prod.sh
```

`deploy-prod.sh` pulls images → runs migrations (`python -m backend.migrate`,
advisory-locked) → `docker compose up -d` → polls
`/api/v1/health/ready` → **auto-rolls back** if the health check fails.

To build images locally instead of pulling:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

Verify:

```bash
curl -k https://localhost/api/v1/health           # {"status":"healthy"}
curl -k https://localhost/api/v1/health/ready      # {"status":"ready",...}
curl -k https://localhost/metrics                  # Prometheus exposition
```

---

## 6. CI/CD

Two GitHub Actions workflows:

### `.github/workflows/ci.yml` — on every push/PR

1. **Backend** — `ruff` lint + `pytest`
2. **Frontend** — `tsc`/`vite` build + `eslint`
3. **Security scan** — `pip-audit` (Python) + `npm audit` (high+)
4. **Docker build** — builds both images (no push) to catch Dockerfile breakage

Lint/test failures **fail fast** and block the merge.

### `.github/workflows/deploy.yml` — on push to deployable refs

1. **Build & push** images to GHCR, tagged `sha-<short>` + `<branch>`
2. **Deploy staging** — feature branches, automatic (`staging` environment)
3. **Deploy production** — `main` only, **manual approval** via the GitHub
   `production` Environment protection rule (required reviewers)

**Branch policy:** `main` = production; feature branches = staging only. No
direct pushes to `main`.

**Required GitHub secrets/environments:** `production` & `staging` environments;
`PROD_HOST` / `PROD_USER` / `PROD_SSH_KEY` / `PROD_DEPLOY_PATH` (and `STAGING_*`
equivalents). Image push uses the built-in `GITHUB_TOKEN`.

---

## 7. Database operations

- **Migrations**: declarative SQLModel schema applied via
  `python -m backend.migrate`. On Postgres it takes a transaction-level
  advisory lock so concurrent containers can't race the DDL. Run automatically
  by the deploy scripts before services start.
- **Connection pooling**: configured per-driver in `backend/database.py`
  (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `pool_pre_ping`). PgBouncer can be added in
  front of `postgres` later without app changes.
- **Backups**: `./scripts/backup-db.sh` (timestamped, gzipped `pg_dump`, with
  retention). Schedule via cron:
  ```cron
  0 3 * * * cd /opt/synapse && ./scripts/backup-db.sh >> /var/log/synapse-backup.log 2>&1
  ```
- **Restore**: `./scripts/restore-db.sh ./backups/<file>.sql.gz`
- **Index/performance audit**: `pg_stat_statements` + `pg_trgm` are enabled by
  `scripts/postgres-init/01-init.sql`. Find hotspots with:
  ```sql
  SELECT query, calls, mean_exec_time
  FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;
  ```

---

## 8. Observability

- **Logs**: structured JSON (`LOG_FORMAT=json`) to stdout — one object per line,
  each carrying the `request_id`. Aggregate with `docker compose logs` or ship
  to your log stack. Same format across `backend` and `worker`.
- **Metrics**: Prometheus exposition at `/metrics`
  (`http_requests_total`, `http_request_duration_seconds`). Point a scrape job
  at `backend:8000/metrics`. (Optional Grafana dashboards can read these.)
- **Tracing**: every request gets an `X-Request-ID` (inbound header honored or
  minted), propagated by the proxy, attached to all logs, and echoed back on the
  response — so a client error can be traced to its exact log lines.

---

## 9. Security baseline

- **Rate limiting** (`RATE_LIMIT_ENABLED=true`): per-client fixed window
  (`429` + `Retry-After`); uses Redis when `REDIS_URL` is set, else in-process.
  Health/metrics are exempt.
- **CORS**: strict allow-list; `*` is rejected in production by validation.
- **Security headers** (`SECURITY_HEADERS_ENABLED=true`): HSTS, `X-Frame-Options`,
  `X-Content-Type-Options`, `Referrer-Policy` (proxy also sets HSTS).
- **Secrets**: never in the repo; injected at runtime (§3).
- **Containers**: backend runs as a non-root user; postgres/redis have no host
  ports; the `internal` network is `internal: true`.
- **Auth/session**: `SECURE_COOKIES=true` and `ACCESS_TOKEN_EXPIRE_MINUTES`
  enforce secure cookie flags + token expiry once auth is enabled.

---

## 10. Rollback

Automatic: a failed post-deploy health check triggers `rollback.sh`, which
redeploys the previously-recorded image tag (`.deploy-state/<env>/previous_tag`).

Manual:

```bash
./scripts/rollback.sh                 # previous production tag
DEPLOY_ENV=staging ./scripts/rollback.sh
./scripts/rollback.sh sha-abc123def0  # explicit tag
```

**Schema note:** migrations are forward-only. Rollback swaps **images**, not the
schema. If a release included a breaking schema change, restore from a backup
(§7) as part of the rollback decision.

---

## 11. Troubleshooting

| Symptom | Check |
|---------|-------|
| Backend exits immediately in prod | Config validation failed — read the startup log line "Invalid production configuration: …" and fix the named vars |
| `502` from proxy | `docker compose ... ps`; backend/frontend healthy? `... logs backend` |
| Readiness `503` | DB unreachable — `... logs postgres`, verify `DATABASE_URL` + `POSTGRES_PASSWORD` |
| `/metrics` returns `503` | `prometheus-client` not installed in the image (rebuild) |
| `429` everywhere | Rate limit too low — tune `RATE_LIMIT_REQUESTS` / `_WINDOW_SECONDS` |
| TLS warning locally | Expected with the self-signed fallback; install real certs for prod |
| Migrations hang | Another container holds the advisory lock — wait or check for a stuck deploy |
| Deploy auto-rolled back | Health check failed; inspect `... logs backend` from the deploy output |

Useful commands:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f backend
docker compose -f docker-compose.prod.yml --env-file .env.production exec backend \
  curl -fsS http://localhost:8000/api/v1/health/ready
```

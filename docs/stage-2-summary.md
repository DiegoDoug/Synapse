# Stage 2 Summary — Integrations

**Status:** Complete
**Outcome:** Personal OS can connect a Google account and ingest real data.
Stage 2 delivers the integration architecture, Google OAuth connection
management, read-only Gmail and Google Calendar integrations, and the
synchronization services that keep local copies of emails and events current.
It establishes the ARCHITECTURE.md Service → Integration contract so later
stages (notifications, AI, agents) build on a stable data and service layer.

This is a backend stage. No frontend, AI, or agent code was written.

---

## Objectives Completed

- **Integration architecture & service interfaces** — explicit contracts
  (`services/interfaces.py`, `integrations/base.py`) and a layered
  Integration → Service → Repository design.
- **Google OAuth connection management** — authorize / callback / list /
  disconnect, with token storage and refresh.
- **Gmail integration** — read-only ingestion of message metadata with
  incremental sync via a `historyId` cursor (full-resync fallback on expiry).
- **Google Calendar integration** — read-only ingestion of events with
  incremental sync via a `syncToken` cursor (full-resync fallback on 410 Gone).
- **Synchronization services** — per-resource sync plus a unifying
  `SyncService` that syncs all resources for an account and reports status.
- **REST API** — 13 endpoints across connections, email, calendar, and sync.

---

## Files Created

**Data models** (`backend/models/`)
- `account.py` — connected account + OAuth credentials
- `sync_state.py` — per-(account, resource) sync cursor + status
- `email_message.py` — synced Gmail message metadata
- `calendar_event.py` — synced Google Calendar event

**Integrations** (`backend/integrations/`)
- `base.py` — `Integration` base contract
- `google/oauth.py` — `GoogleOAuthClient` (auth-code flow, token exchange/refresh, userinfo)
- `google/gmail.py` — `GmailIntegration` (profile, list, history, get)
- `google/calendar.py` — `GoogleCalendarIntegration` (events list with syncToken)

**Services** (`backend/services/`)
- `interfaces.py` — `Connection/Email/Calendar/Sync` service interfaces
- `connection_service.py` — `ConnectionService`
- `email_service.py` — `EmailService` (incremental Gmail sync + mapping)
- `calendar_service.py` — `CalendarService` (incremental Calendar sync + mapping)
- `sync_service.py` — `SyncService` (cross-resource orchestration + status)

**Repositories** (`backend/repositories/`)
- `account_repository.py`, `sync_state_repository.py`,
  `email_repository.py`, `calendar_repository.py`

**Schemas** (`backend/schemas/`)
- `connection.py`, `sync.py`, `email.py`, `calendar.py`

**API** (`backend/api/`)
- `routes/connections.py`, `routes/email.py`, `routes/calendar.py`, `routes/sync.py`

**Tests**
- `backend/tests/test_stage2_integrations.py` — API wiring + Gmail sync mapping

**Docs**
- `docs/stage-2-summary.md` — this file

## Files Modified

- `backend/models/__init__.py` — register the four new models
- `backend/api/dependencies.py` — current-owner user + service/integration DI
- `backend/api/routes/__init__.py` — mount the new routers
- `backend/config.py` / `backend/.env.example` — Google OAuth + sync settings
- `backend/requirements.txt` — google-auth(-oauthlib), google-api-python-client,
  apscheduler, httpx
- `backend/pyproject.toml` — mark FastAPI `Depends`/`Query` as immutable (B008)
- `CURRENT_SPRINT.md` — Stage 2 spec, then advanced to Stage 3

---

## Architectural Decisions

- **Service → Integration contract enforced.** Integrations are thin HTTP/SDK
  clients with no DB access; services hold business logic and orchestrate
  repositories. No agents were introduced (deferred to Stage 6).
- **Official Google client libraries** (`google-auth-oauthlib`,
  `google-api-python-client`) for robust OAuth token refresh and REST access,
  rather than hand-written httpx calls.
- **Per-account integration construction.** Integrations need per-account
  credentials, so services build them via a small factory step from the
  account's refreshed credentials — a pragmatic reading of the "DI-instantiated
  integration" guidance, which targets stateless clients.
- **Incremental sync with provider cursors** stored in `SyncState`: Gmail
  `historyId` (404 → full resync) and Calendar `syncToken` (410 → full resync).
- **Synchronous service/DB layer** to match the existing sync `get_session`
  SQLModel pattern; FastAPI runs these in its threadpool.
- **Single-owner user** via a `get_current_user_id` dependency that lazily
  creates one owner — there is no auth stage yet.
- **OAuth optional at boot.** Without `GOOGLE_CLIENT_ID/SECRET` the app still
  starts; connection/email/calendar routes return `503` until configured.

---

## Verification

- `ruff check backend/` — passes
- `pytest backend/tests/` — 7 passed
- App boots; 13 endpoints registered (verified via OpenAPI schema)
- No live Google calls were made; the integration layer is faked in tests.
  End-to-end OAuth against real Google credentials has not been exercised in
  this environment.

---

## Unresolved Issues / Technical Debt

- **No live OAuth verification.** The flow is implemented to spec but not run
  against real Google credentials here; first real connection should be smoke-
  tested manually.
- **Single-user assumption.** Connections attach to one lazily-created owner
  user; multi-user requires a real auth stage.
- **No scheduled sync yet.** APScheduler is a dependency and
  `SYNC_INTERVAL_MINUTES` exists, but sync is currently manual (via endpoints).
- **Read-only by design.** Sending email / creating events is intentionally out
  of scope until Stage 4.5.
- **Token storage is plaintext** in SQLite — acceptable for a local personal
  device now; encrypt-at-rest when moving to Postgres/production (Stage 8).
- **No frontend.** Synced data is API-only; wiring widgets to these endpoints
  is a follow-up.

---

## Recommendations for Stage 3 (Notifications)

- Use the synced `EmailMessage` / `CalendarEvent` data as notification sources
  (daily summaries, upcoming-event reminders).
- Add the APScheduler job that calls `SyncService.sync_account` on
  `SYNC_INTERVAL_MINUTES`, then trigger notifications off fresh data.
- Reuse the connection/integration pattern for the Telegram bot integration.

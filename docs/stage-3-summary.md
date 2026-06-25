# Stage 3 Summary — Notifications & Telegram Integration

**Status:** Complete
**Outcome:** Personal OS now turns synced data into timely, useful messages. It
delivers a persisted notification center (reminders, alerts, daily summaries),
external delivery through a Telegram bot, scheduled composition/delivery jobs,
and basic inbound bot commands. It builds directly on the Stage 2 sync services
and the ARCHITECTURE.md Service → Integration contract.

This is a backend-plus-frontend stage. No AI, agents, or write-to-external-API
features were introduced (deferred to Stages 4 / 4.5 / 6).

Stage 3 was delivered in two major features, each merged on the
`feature/notifications-telegram` branch:

- **Major Feature 1 — in-app notification center** (PR #12, merged): model,
  service, repository, REST endpoints, and UI, with no external delivery.
- **Major Feature 2 — Telegram delivery & scheduled jobs**: the Telegram
  integration, delivery, APScheduler jobs, and inbound commands.

---

## Objectives Completed

- **Notification architecture & model** — a persisted `Notification` with
  classification (category/priority), provenance (`source`/`source_key` for
  dedupe), read state, and delivery state.
- **NotificationService** — center reads (list/counts), state changes
  (mark read / mark all read), manual creation, and rule-based composition of
  reminders (upcoming events) and alerts (unread email) from synced data. No
  AI/analysis — metadata-only rules.
- **Notification center** — REST endpoints + a React notification center page,
  a sidebar entry with an unread badge, and a live dashboard widget.
- **Telegram integration** — a thin HTTP client (`TelegramIntegration`) plus a
  `TelegramService` for inbound command routing (`/help`, `/summary`,
  `/unread`).
- **Delivery** — send one / deliver pending / compose-and-deliver / daily
  summary, with per-notification delivery state and idempotent daily summaries.
- **Scheduling** — APScheduler jobs (interval poll+deliver, daily-summary cron,
  Telegram command polling) wired into the app lifespan; the scheduler only
  triggers services.

---

## Files Created

**Major Feature 1**

- `backend/models/notification.py` — `Notification` table
- `backend/schemas/notification.py` — notification DTOs
- `backend/repositories/notification_repository.py` — `NotificationRepository`
- `backend/services/notification_service.py` — `NotificationService`
- `backend/api/routes/notifications.py` — notification-center endpoints
- `backend/tests/test_stage3_notifications.py` — center CRUD + composition tests
- `frontend/src/features/notifications/` — `api.ts`, `useNotifications.ts`,
  `format.ts`, `components/NotificationItem.tsx`, `components/NotificationList.tsx`
- `frontend/src/pages/NotificationsPage.tsx` — notification center view

**Major Feature 2**

- `backend/integrations/telegram/__init__.py`, `backend/integrations/telegram/bot.py`
  — `TelegramIntegration` (httpx HTTP client)
- `backend/services/telegram_service.py` — `TelegramService` (inbound commands)
- `backend/services/factory.py` — shared construction of the notification stack
- `backend/scheduler.py` — APScheduler wiring
- `backend/tasks/__init__.py`, `backend/tasks/notification_tasks.py` — job callables
- `backend/tests/test_stage3_telegram.py` — delivery, command, scheduler tests

**Docs**

- `docs/stage-3-summary.md` — this file

## Files Modified

- `backend/models/__init__.py` — register `Notification`
- `backend/services/interfaces.py` — `NotificationServiceInterface`
- `backend/api/dependencies.py` — notification-service provider (via factory)
- `backend/api/routes/__init__.py` — mount the notifications router
- `backend/config.py` / `backend/.env.example` — Telegram + scheduler settings
- `backend/main.py` — start/stop the scheduler in the app lifespan
- `backend/requirements.txt` — note Stage 3 use of apscheduler + httpx
- `frontend/src/api/client.ts` — `apiPost`
- `frontend/src/App.tsx` — `/notifications` route
- `frontend/src/components/layout/Sidebar.tsx` — nav entry + unread badge
- `frontend/src/features/dashboard/components/NotificationsWidget.tsx` — live data
- `frontend/src/pages/SettingsPage.tsx` — Telegram status card
- `CURRENT_SPRINT.md` — Stage 3 spec, then advanced to Stage 4

---

## Architectural Decisions

- **Service → Integration contract enforced.** `TelegramIntegration` is a thin
  HTTP client with no business logic; `NotificationService` and
  `TelegramService` hold the logic. Inbound command routing lives in a service,
  not the integration.
- **httpx over a bot framework.** Telegram delivery uses httpx (already a
  dependency) instead of `python-telegram-bot`, keeping the integration a true
  thin client and avoiding an async framework dependency.
- **Rule-based composition, no AI.** Notifications are composed from synced
  metadata (upcoming events, unread email) — no content analysis or LLMs
  (Stage 4+). Composition is idempotent via a stable `source_key`.
- **Scheduler only triggers services.** APScheduler jobs are thin and
  best-effort; all composition/formatting/delivery lives in the service layer.
  An optional Stage 2 sync runs first when Google is configured.
- **Single construction point** (`services/factory.py`) shared by DI, the
  scheduler, and tasks, so the notification stack is wired the same way
  everywhere.
- **Graceful degradation.** With no bot token, delivery endpoints report
  `configured: false`, the command-poll job is not registered, and the UI shows
  a "not configured" hint — the app runs in-app-only with zero config.
- **In-memory Telegram offset.** A single long-lived `TelegramService` holds the
  update offset; acceptable for the single-user, long-running process.

---

## Verification

- `ruff check backend` — passes
- `pytest backend` — 23 passed (13 notification center + 10 Telegram/scheduler)
- `TelegramIntegration` HTTP path verified against a local mock server (URL,
  payload, parsing, error handling)
- Scheduler starts cleanly in the app lifespan; registers the expected jobs with
  and without a configured bot
- Frontend `tsc -b`, `eslint`, and `vite build` all clean
- No live Telegram calls in CI; the integration is faked/mock-served in tests

---

## Unresolved Issues / Technical Debt

- **No live Telegram verification.** Delivery and commands are implemented to
  spec and verified against a mock server, but not exercised against a real bot
  token in this environment; first real send should be smoke-tested manually.
- **Telegram update offset is in-memory.** It resets on process restart;
  Telegram only retains ~24h of updates, so this is acceptable for now but could
  be persisted (e.g. a dedicated cursor row) if needed.
- **Single-chat delivery.** Delivery targets one default chat id; multi-recipient
  / per-user routing waits on a real auth/multi-user stage.
- **Scheduled Google sync is best-effort.** The poll job triggers Stage 2 sync
  only when Google is configured and swallows per-account failures (logged,
  surfaced via `SyncState`).
- **Plaintext token config.** Bot token lives in env/SQLite-adjacent config;
  encrypt-at-rest belongs with the Stage 8 production move.

---

## Recommendations for Stage 4 (AI Layer)

- Reuse the Service → Integration contract for LLM providers: an `AIService`
  (logic, tool-use loop) over thin provider integrations (Anthropic primary).
- Surface notification/center data and synced email/calendar reads as read-only
  AI tools via a `ToolRegistry`.
- Consider a "summarize my notifications / day" capability that composes the
  daily summary text through the AI layer rather than the current rule-based
  string (keeping the rule-based path as a no-LLM fallback).
- Stream responses via SSE; keep the synchronous service/DB layer pattern.

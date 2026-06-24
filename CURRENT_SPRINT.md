# Current Sprint

Current Stage: Stage 3

Objective:

Add a notification layer on top of the Stage 2 integrations: a Telegram bot,
push notifications, and an in-app notification center. The system should turn
synced data (emails, calendar events) into timely, useful messages — daily
summaries, reminders, and alerts — and accept simple commands.

This is a backend-plus-frontend stage. It builds directly on the Stage 2
synchronization services and the Service → Integration contract.

---

# Allowed Features

Backend:

- Telegram bot integration (delivery + simple inbound commands)
- a `NotificationService` that composes notifications from synced data
- a `Notification` model + persistence (notification history / center)
- scheduled jobs (APScheduler) for daily summaries and reminders
- REST endpoints for the notification center (list / mark read)

Frontend:

- notification center UI (list, unread state, mark read)
- surfacing alerts/reminders in the dashboard shell

---

# Architecture Contract

Per ARCHITECTURE.md (Service → Integration contract):

- **Integration layer** — `TelegramIntegration` (HTTP only, no business logic).
- **Service layer** — `NotificationService` composes and dispatches
  notifications; orchestrates repositories and the Telegram integration.
- **Repository layer** — `NotificationRepository` for persistence.
- **Scheduling** — APScheduler triggers run sync (Stage 2 `SyncService`) and
  then compose notifications; no notification logic lives in the scheduler.
- Agents are **not** introduced in this stage (Stage 6).

---

# Restrictions

DO NOT implement:

- AI systems (chat, LLM routing, prompts, tool use) — Stage 4
- agents / agent orchestration — Stage 6
- embeddings, vector search, RAG — Stage 5
- voice — Stage 4.7
- write operations to external APIs beyond Telegram delivery
  (no send-email / create-event — Stage 4.5)
- PostgreSQL / Redis / Docker — Stage 8

Do not implement future stages beyond Stage 3.

---

# Deliverables

- Telegram bot integration (delivery + basic commands)
- notification composition from synced emails/events
- notification center (model, persistence, REST endpoints, UI)
- scheduled daily summaries and reminders (APScheduler)

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
Notification model + `NotificationService` + notification-center REST endpoints
and UI (in-app notifications, no external delivery yet).

Major Feature 2:
`TelegramIntegration` + delivery + scheduled daily summaries / reminders
(APScheduler), plus basic inbound commands.

After each major feature:

- explain decisions
- list files created / modified
- wait for approval

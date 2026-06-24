# Current Sprint

Current Stage: Stage 2

Objective:

Connect Personal OS to external accounts and bring real data in. This stage
adds Google account connections (OAuth), Gmail and Google Calendar
integrations, and the synchronization services that keep local copies of
emails and events up to date.

This is a backend stage. It establishes the Service → Integration contract
defined in ARCHITECTURE.md so that later stages (AI, agents, automation) have a
stable data and service layer to build on.

---

# Allowed Features

Backend:

- account connections via Google OAuth 2.0 (connect / list / disconnect)
- Gmail integration (read-only ingestion of message metadata)
- Google Calendar integration (read-only ingestion of events)
- synchronization services (incremental sync with per-account cursors)
- connection management (token storage + refresh)
- REST endpoints exposing connections, emails, and calendar events

---

# Architecture Contract

Per ARCHITECTURE.md (Service → Integration contract):

- **Integration layer** (`backend/integrations/`) — thin external API clients
  (`GoogleOAuthClient`, `GmailIntegration`, `GoogleCalendarIntegration`).
  HTTP/SDK calls only, no business logic, no DB access.
- **Service layer** (`backend/services/`) — business logic
  (`ConnectionService`, `EmailService`, `CalendarService`, `SyncService`).
  Orchestrates repositories and integrations. No direct HTTP.
- **Repository layer** (`backend/repositories/`) — data access only.
- **Interfaces** (`backend/services/interfaces.py`,
  `backend/integrations/base.py`) — explicit contracts so implementations are
  swappable and testable via dependency injection.
- Agents are **not** introduced in this stage (Stage 6). Integrations must
  never be called by agents; services must never make HTTP calls directly.

Data model (`backend/models/`):

- `Account` — a connected external account (provider, email, OAuth tokens).
- `SyncState` — per-account, per-resource sync cursor + status.
- `EmailMessage` — synced Gmail message metadata.
- `CalendarEvent` — synced Google Calendar event.

---

# Restrictions

DO NOT implement:

- AI systems (chat, LLM routing, prompts, tool use) — Stage 4
- agents / agent orchestration — Stage 6
- notifications / Telegram — Stage 3
- embeddings, vector search, RAG — Stage 5
- voice — Stage 4.7
- write operations to external APIs (send email, create event) — Stage 4.5
  (this stage is read-only ingestion + connection management only)
- PostgreSQL / Redis / Docker — Stage 8

Do not implement future stages beyond Stage 2.

---

# Deliverables

- Integration architecture and service interfaces
- Google OAuth connection flow + connection management
- Gmail integration with incremental email synchronization
- Google Calendar integration with incremental event synchronization
- Synchronization services (manual trigger now; scheduled sync deferred)
- REST endpoints for connections, emails, and calendar events

---

# Development Process

Phase A — Foundation:
Integration architecture, service interfaces, shared data models
(`Account`, `SyncState`, `EmailMessage`, `CalendarEvent`), repositories, DTO
schemas, configuration, and dependencies.

Phase B — Gmail (requires approval):
Google OAuth + connection management, `GmailIntegration`, `EmailService`,
email synchronization, and connection/email routes.

Phase C — Google Calendar (requires approval):
`GoogleCalendarIntegration`, `CalendarService`, event synchronization, and
calendar routes.

After each phase:

- explain decisions
- list files created / modified
- wait for approval before the next integration

# Current Sprint

Current Stage: Stage 2

Objective:

Connect Personal OS to external accounts and synchronize their data —
starting with Gmail and Google Calendar — through a clean service +
integration layer.

---

# Allowed Features

Backend:

- OAuth account connection (Google)
- Gmail integration (read/sync messages)
- Google Calendar integration (read/sync events)
- Connection management (connect, list, disconnect)
- Synchronization services
- Models for connected accounts and synced data

Frontend:

- Connections / accounts management UI
- Connection status indicators
- Surface synced email and calendar data in existing dashboard widgets

---

# Architecture Contract

Each external system must follow ARCHITECTURE.md:

- A named Service (e.g. EmailService, CalendarService) — business logic, no HTTP
- A named Integration (e.g. GmailIntegration, GoogleCalendarIntegration) — HTTP client, no business logic

Create the backend/integrations/ package in this stage.

Services never call external APIs directly; they call integrations.
Integrations contain no business logic.

---

# Database Models

Create:

- Connection (linked external account: provider, tokens, status)
- EmailMessage (synced email metadata)
- CalendarEvent (synced calendar event)

---

# API

Implement (under /api/v1):

- account connection + OAuth callback endpoints
- list / disconnect connections
- list synced emails
- list synced calendar events

---

# Restrictions

DO NOT implement:

- AI systems / agents
- Telegram or notifications
- embeddings / vector databases / RAG
- voice
- write actions to external services (send email, create events) — read/sync only

Do not implement future stages beyond Stage 2.

---

# Deliverables

- Google account connection works (OAuth)
- email synchronization
- calendar synchronization
- connection management (connect / list / disconnect)
- secrets handled via configuration (no committed credentials)

---

# Development Process

Step 1:
Integration layer scaffolding + Connection model + OAuth config.

Step 2:
Google OAuth connection flow + connection management.

Step 3:
Gmail integration + EmailService + email sync.

Step 4:
Google Calendar integration + CalendarService + event sync.

Step 5:
Frontend connections UI + surface synced data.

After each step:

- explain decisions
- list files created
- wait for approval

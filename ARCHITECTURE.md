# Personal OS — System Architecture

**Instruction precedence:** CURRENT_SPRINT.md > ROADMAP.md > ARCHITECTURE.md > GOVERNANCE.md > CLAUDE.md

This document describes the runtime architecture of Personal OS: the layers, components, and dependencies that form the application. It sits above GOVERNANCE.md and CLAUDE.md in the instruction hierarchy — architectural decisions here override coding style preferences.

Related documents:
- **CLAUDE.md** — product vision, workflow, sprint process (overridden by this document)
- **GOVERNANCE.md** — principles and standards (overridden by this document)
- **ROADMAP.md** — product roadmap (overrides this document)
- **CURRENT_SPRINT.md** — active development stage (overrides everything)

---

## System Overview

```
                    Personal OS
                   (Unified UX)
                         │
        ┌────────────────┼────────────────┐
        │                │                │
      Frontend          Backend         Database
   (React + TS)      (FastAPI)         (SQLite)
        │                │                │
        │         Service Layer          │
        │                │                │
        │         ┌───────┴───────┐      │
        │         │               │      │
        │    Integration      Repository  │
        │    Layer            Layer      │
        │         │               │      │
        │    ┌────┴────┐          │      │
        │    │         │          │      │
        │  Gmail   Calendar   Other      │
        │  APIs     APIs      APIs       │
        │
      Agents
    (AI Layer)
```

---

## Architectural Style

**Modular Monolith**

The application is a single deployable unit (one server, one database) but organized into independent modules that could later be split into microservices without rewriting code.

**Rationale:**
- Monolith: simpler ops, faster iteration, easier debugging during early stages
- Modular: prepared for scale; can extract services without refactoring
- Supports the current roadmap (Stages 1–7) without overengineering

---

## Backend Stack

### Core Framework

- **Python 3.12** — type hints, pattern matching, performance
- **FastAPI** — async HTTP framework, auto OpenAPI docs, dependency injection
- **SQLModel** — ORM + schema validation (unifies Pydantic + SQLAlchemy)
- **Pydantic v2** — runtime validation, serialization

### Persistence

- **SQLite** (current) — file-based, zero-ops for prototyping
- **PostgreSQL** (future) — scalable, reliable, ACID
- **Redis** (future) — caching, job queue
- **Qdrant** (future) — vector embeddings for RAG

### Scheduling & Jobs

- **APScheduler** — run async tasks on a schedule (e.g., sync Gmail every 5min)

### Structure

```
backend/
  ├── main.py                 # FastAPI app, startup/shutdown hooks
  ├── models/                 # SQLModel definitions
  ├── services/               # Business logic (no DB access)
  ├── repositories/           # Data access layer (queries, transactions)
  ├── integrations/           # External API clients (Gmail, Calendar, etc.)
  ├── agents/                 # AI agent orchestration
  ├── schemas/                # Pydantic request/response models
  └── api/
      ├── routes/             # Endpoint handlers
      └── dependencies.py     # FastAPI dependency injection
```

**Dependency Flow:**
```
HTTP Route → Service → Repository → SQLModel
                ↓
           Integration (Gmail, etc.)
                ↓
           External API
```

Services never call integrations directly; they ask a repository or another service. Integrations are instantiated by the route handler via dependency injection.

**Service → Integration contract (required for Stage 2+):**

Each external system must have:
1. A named **Service** (`EmailService`, `CalendarService`) — business logic, no HTTP calls
2. A named **Integration** (`GmailIntegration`, `GoogleCalendarIntegration`) — HTTP client, no business logic
3. A named **Agent** (`EmailAgent`, `CalendarAgent`) — orchestrates Service, never calls Integration directly

```
EmailAgent
    ↓ calls
EmailService
    ↓ calls
GmailIntegration
    ↓ calls
Gmail API
```

Agents must never reference integrations. Integrations must never contain business logic.

---

## Frontend Stack

### UI Framework

- **React 18** — component-based, hooks, concurrent features
- **TypeScript** — strict, no `any`, full type safety
- **Vite** — fast bundler, fast HMR, minimal config

### Styling

- **Tailwind CSS** — utility-first, dark mode support, consistent design system

### State & Data

- **Zustand** — minimal store (atoms of state, no boilerplate)
- **React Query** — server state management (caching, invalidation, sync)
- **React Router** — client-side navigation

### Components & Design

- **shadcn/ui** — unstyled, accessible component library (copy & customize)
- **Magic UI** — pre-built landing page components

### Structure

```
frontend/
  ├── main.tsx                # Entry point
  ├── App.tsx                 # Root router
  ├── pages/                  # Route pages (Page.tsx per route)
  ├── features/               # Feature modules (feature-based, not layer-based)
  │   ├── dashboard/
  │   │   ├── components/
  │   │   ├── hooks/
  │   │   ├── stores/
  │   │   ├── types.ts
  │   │   └── api.ts          # Queries & mutations
  │   ├── email/
  │   ├── calendar/
  │   └── ...
  ├── components/             # Shared components (Button, Card, etc.)
  ├── hooks/                  # Shared hooks (useNotification, etc.)
  ├── store/                  # Global state (Zustand)
  ├── api/                    # API client (fetch wrapper, types)
  ├── types/                  # Shared TypeScript types
  ├── utils/                  # Helpers (formatting, parsing, etc.)
  └── styles/                 # Global Tailwind overrides, CSS variables
```

**State Hierarchy:**
```
Global Store (Zustand)
    ├── Auth (user session)
    ├── UI (theme, sidebar state)
    └── Notifications (toast messages)

Feature Stores (Zustand per feature)
    ├── Email drafts, filter state
    ├── Calendar view (week/month/day)
    └── Dashboard widget config

Server State (React Query)
    ├── Emails (cached list, mutations)
    ├── Calendar events (cached, real-time sync)
    └── Tasks (cached, auto-refresh)
```

---

## Database

### Current (Stage 1)

**SQLite** — file at `data/synapse.db`

- Zero operations overhead
- Perfect for prototyping
- Suitable for personal device

### Future (Post-Stage 1)

**PostgreSQL** — external server

- Multi-user support
- Advanced query features
- Cloud deployment

### Schema

Defined in `backend/models/` using SQLModel:
- Strict type hints
- Pydantic validation on write
- SQLAlchemy ORM on read

---

## Integrations & External APIs

Services connect to external systems through a **service layer + integration layer** to avoid tight coupling:

```
Frontend                Backend             External
   │                       │                   │
   ├─ /api/email ────────→ Email Service      │
   │                           │               │
   │                      Gmail Integration    │
   │                           │               │
   │                    (requests Gmail API) ──┤
   │                                           │
   │         (Email Service returns results)   │
   │←──────────────────────────────────────────┘
```

### Current Integrations

- **Gmail** — email ingestion, send
- **Google Calendar** — event sync, create
- **Telegram** — notification delivery
- **LLM APIs** — inference (for agents)

### Future Integrations

- **Canvas** — notetaking sync
- **Slack** — team communication
- **Notion** — knowledge base sync
- **Qdrant** — vector search (RAG backend)

---

## Agents (AI Layer)

Agents orchestrate multi-step workflows using LLMs and integrations.

**Not yet implemented** (planned for Stage 6).

Expected structure:
```
backend/agents/
  ├── base.py                 # Agent interface
  ├── email_agent.py          # Email automation
  ├── calendar_agent.py       # Calendar automation
  ├── study_agent.py          # Study assistance
  ├── notification_agent.py   # Smart notifications
  └── prompts/                # Agent system prompts
```

---

## Deployment & Infrastructure

### Current (Stage 1)

- **Single machine** — develop locally, test on laptop
- **SQLite** — file-based persistence
- **No Docker** — bare Python, venv

### Future (Post-Stage 1)

- **Docker** — containerized backend + frontend
- **PostgreSQL** — managed database
- **Redis** — job queue, cache
- **Kubernetes** (optional) — multi-instance scaling

---

## Key Architectural Decisions

| Decision | Rationale |
| -------- | --------- |
| **Modular Monolith** | Fast iteration now, scalable later |
| **FastAPI + SQLModel** | Async, type-safe, minimal boilerplate |
| **Zustand + React Query** | Lightweight state (no Redux complexity) |
| **Feature-based FE structure** | Scales from 10 to 100+ pages cleanly |
| **Service layer** | Decouples integrations from business logic |
| **Dependency injection** | Makes testing and swapping implementations easy |
| **Dark mode first** | Modern product positioning, better for focus UX |

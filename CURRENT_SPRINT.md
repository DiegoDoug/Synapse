# Current Sprint

Current Stage: Stage 4

Objective:

Add the AI layer on top of the Stage 1–3 foundation: a chat interface backed by
multi-provider LLM routing, a prompt system, and a tool-use (function-calling)
framework with read-only tools over the synced data. The AI can answer
questions, summarize, and recommend using the user's emails, calendar, and
notifications as context — and can look up information on the web read-only.

This is a backend-plus-frontend stage. It builds on the Stage 2 sync data and
the ARCHITECTURE.md Service → Integration contract.

---

# Allowed Features

Backend:

- `AIService` — routes prompts to a provider and runs the tool-use loop
- multi-provider LLM routing (Anthropic primary; OpenAI secondary; Ollama local)
- a prompt system (system prompts, context assembly)
- a `ToolRegistry` mapping tool names to backend service calls
- read-only AI tools: search emails, get calendar events, get notifications
- informational web browsing: a read-only `BrowserService` (Playwright headless)
  to navigate URLs and extract content
- streaming responses via SSE

Frontend:

- AI chat interface (message list, streaming responses, context indicators)
- surfacing tool calls / sources in the chat UI

---

# Architecture Contract

Per ARCHITECTURE.md (Service → Integration contract):

- **Integration layer** — thin provider clients (Anthropic/OpenAI/Ollama HTTP)
  and `BrowserService` (Playwright headless), no business logic.
- **Service layer** — `AIService` owns the prompt assembly and tool-use loop;
  the `ToolRegistry` maps tool names to existing services' read methods.
- **Read-only tools only** — tools call existing service reads (email/calendar/
  notification). No writes to internal CRUD or external APIs in this stage.
- Agents are **not** introduced in this stage (Stage 6).

---

# Restrictions

DO NOT implement:

- write tools / confirmation system (create/update/delete, send email,
  create event, send Telegram via AI) — Stage 4.5
- voice (STT/TTS/wake word) — Stage 4.7
- embeddings, vector search, RAG — Stage 5
- agents / agent orchestration — Stage 6
- workflow automation / Playwright write/automation — Stage 7
- PostgreSQL / Redis / Docker — Stage 8

Browser tools are read-only in this stage (navigate + extract). Do not implement
future stages beyond Stage 4.

---

# Deliverables

- `AIService` with provider routing and a working tool-use loop
- a prompt system + `ToolRegistry` with read-only tools
- read-only `BrowserService` (navigate URL + extract content)
- SSE streaming endpoint(s) for chat
- an AI chat interface in the frontend

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
`AIService` + provider routing + prompt system + a non-streaming chat endpoint
and a minimal chat UI (no tools yet).

Major Feature 2:
`ToolRegistry` + read-only tools + the tool-use loop + SSE streaming, plus the
read-only `BrowserService` for web lookups, surfaced in the chat UI.

After each major feature:

- explain decisions
- list files created / modified
- wait for approval

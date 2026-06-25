# Current Sprint

Current Stage: Stage 4.5

Objective:

Extend the Stage 4 AI layer from read-only to **action-capable**, safely. Add
write tools behind the existing `ToolRegistry` — internal CRUD and external API
writes — gated by a confirmation system so destructive or outbound actions
require explicit user approval before they execute. Promote the read-only
`BrowserService` to limited, confirmed write (form fill + submit).

This is a backend-plus-frontend stage. It builds on the Stage 4 `AIService` +
tool-use loop, the Stage 2 OAuth/sync services, and the Stage 3 Telegram
delivery, all under the ARCHITECTURE.md Service → Integration contract.

---

# Allowed Features

Backend:

- write tools behind the `ToolRegistry`:
  - internal CRUD: `create_task`, `update_task`, `delete_task`,
    `update_widget_config`
  - external (requires Stage 2 OAuth / Stage 3 Telegram): `send_email`,
    `create_calendar_event`, `delete_calendar_event`, `send_telegram_message`
- a `PendingAction` model (DB) storing a proposed action + payload + status
- a `ConfirmationService` that creates pending actions and listens for approval
- a `ToolExecutor` that runs approved actions through the service layer
- `BrowserService` limited write: `fill_form` + `submit` (with confirmation),
  plus `extract_structured_data` and `take_screenshot`

Frontend:

- a `ConfirmationModal` that surfaces pending actions for approve/reject
- pending-action state surfaced in the chat UI (e.g. over the SSE channel)

---

# Confirmation Model

Per ROADMAP Stage 4.5:

- **Reads** — autonomous (no confirmation); unchanged from Stage 4
- **Creates** — autonomous
- **Updates** — require user approval before execution
- **Deletes** — require user approval before execution

Browser writes (`fill_form` + `submit`) always require confirmation.

---

# Architecture Contract

- **Integration layer** — provider clients and `BrowserService` stay thin; new
  external writes reuse the existing Gmail / Calendar / Telegram integrations.
- **Service layer** — `ConfirmationService` owns the pending-action lifecycle;
  `ToolExecutor` runs approved actions through existing services. Write tools
  map to service write methods, never to integrations directly.
- **Read-only tools are unchanged** — Stage 4 read tools keep running
  autonomously inside the tool-use loop.
- Agents are **not** introduced in this stage (Stage 6).

---

# Restrictions

DO NOT implement:

- agents / agent orchestration — Stage 6
- voice (STT/TTS/wake word) — Stage 4.7
- embeddings, vector search, RAG — Stage 5
- workflow automation / scheduled Playwright automation — Stage 7
- PostgreSQL / Redis / Docker — Stage 8

Autonomous, unconfirmed destructive actions are out of scope: updates and
deletes must pass through the confirmation flow. Do not implement future stages
beyond Stage 4.5.

---

# Deliverables

- `PendingAction` model + `ConfirmationService` + `ToolExecutor`
- write tools (internal CRUD + external API writes) behind the `ToolRegistry`
- the confirmation flow end-to-end (propose → approve/reject → execute)
- `BrowserService` confirmed write (`fill_form` + `submit`) + `take_screenshot`
- a `ConfirmationModal` and pending-action surfacing in the chat UI

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
`PendingAction` + `ConfirmationService` + `ToolExecutor` + internal write tools
(task CRUD, widget config) with the confirmation flow and `ConfirmationModal`.

Major Feature 2:
external write tools (Gmail / Calendar / Telegram) and `BrowserService` confirmed
write (form fill + submit) + screenshot, surfaced in the chat UI.

After each major feature:

- explain decisions
- list files created / modified
- wait for approval

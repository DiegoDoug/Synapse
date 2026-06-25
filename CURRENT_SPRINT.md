# Current Sprint

Current Stage: Stage 6

Objective:

Give Personal OS an **agent layer**: domain agents that orchestrate the existing
services into **autonomous multi-step workflows**, composing the Stage 4 read
tools and Stage 4.5 write tools without per-step user prompting. Agents plan and
act through the service layer; they never call integrations directly. Grounding
(Stage 5 `search_knowledge`) and the existing chat/confirmation core are reused,
not rewritten.

This is a backend-plus-frontend stage. It builds on the Stage 4 `AIService` +
`ToolRegistry`, the Stage 4.5 `ConfirmationService` / `ToolExecutor`, and the
ARCHITECTURE.md **Agent → Service → Integration** contract.

---

# Allowed Features

Backend:

- a `backend/agents/` package with a base `Agent` interface (a plan→act→observe
  loop over the existing tools) and a small **agent runner** that records each
  run's steps, tool calls, status, and result
- domain agents that orchestrate **services** (never integrations):
  - `EmailAgent`, `CalendarAgent`, `StudyAgent`, `NotificationAgent`
- agents compose the existing `ToolRegistry` tools (read + Stage 4.5 write); no
  new side-effect paths are introduced
- an `AgentRun` model (DB) + repository persisting a run's steps and outcome for
  visibility and an audit trail
- REST: list available agents, start an agent run, fetch a run's status/steps,
  list recent runs

Frontend:

- an agents view: trigger an agent, watch its steps stream/update, and review
  past runs (read-only)

---

# Architecture Contract

- **Agent → Service → Integration** — agents call services (or compose tools that
  call services); they must never reference integrations directly, and
  integrations must never contain business logic.
- **Reuse, don't fork** — agents drive the existing `ToolRegistry` /
  `ToolExecutor`; the chat tool-use loop and the Stage 4.5 confirmation flow are
  reused unchanged. RAG retrieval (`search_knowledge`) is available to agents.
- **Auditability** — every agent run persists its steps and any destructive
  action to the `AgentRun` audit trail. Agents may run tool chains with reduced
  interactive confirmation, but destructive operations are always logged.
- **Graceful degradation** — an agent run reports a clear failure step when a
  required service/provider is unavailable rather than crashing the app.

---

# Restrictions

DO NOT implement:

- scheduled workflows / event-driven triggers / a workflow composer — Stage 7
- PostgreSQL / Redis / Docker — Stage 8
- new external integrations or changes to the Stage 4.5 confirmation mechanics
  beyond how agents invoke it
- changes to the Stage 5 retrieval core (reuse `search_knowledge` as-is)
- voice changes — Stage 4.7 is complete

Do not implement future stages beyond Stage 6.

---

# Deliverables

- a `backend/agents/` package: base `Agent` + runner, and the `EmailAgent`,
  `CalendarAgent`, `StudyAgent`, and `NotificationAgent` orchestrating services
- an `AgentRun` model + repository (steps + outcome audit trail)
- REST endpoints to list agents, start a run, and read run status/steps/history
- an agents UI: trigger a run, observe its steps, and review past runs

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
The agent framework — base `Agent` interface + runner over the existing
`ToolRegistry`, the `AgentRun` model + repository, and one reference agent
(e.g. `NotificationAgent` or `StudyAgent`) end-to-end with REST + a minimal UI.

Major Feature 2:
The remaining domain agents (Email, Calendar, Study/Notification) plus the agent
run-history + step-visibility UI.

After each major feature:

- explain decisions
- list files created / modified
- wait for approval

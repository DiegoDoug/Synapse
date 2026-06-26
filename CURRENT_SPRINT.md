# Current Sprint

Current Stage: Stage 7

Objective:

Give Personal OS an **automation layer**: run the Stage 6 agents and the
existing tools **on a schedule and in response to events**, and let the user
**compose tools into named workflow sequences**. Automation is orchestration on
top of what already exists — it starts agent runs and tool chains through the
service layer; it never calls integrations directly and introduces no new
side-effect path. The Stage 6 `AgentService` / `AgentRunner`, the Stage 4.5
confirmation flow, and the Stage 5 retrieval core are reused, not rewritten.

This is a backend-plus-frontend stage. It builds on APScheduler (already a
dependency, used for Stage 3 notification jobs), the Stage 6 agent layer, and the
ARCHITECTURE.md **Agent → Service → Integration** contract.

---

# Allowed Features

Backend:

- a scheduling layer that can **start agent runs and tool chains** on a cron/
  interval schedule, reusing `AgentService` / `AgentRunner` unchanged
- **event-driven triggers** that start an automation in response to an internal
  event (e.g. new synced email → run `EmailAgent`); triggers are evaluated
  against already-synced data, not by calling integrations directly
- a **workflow composer**: persist named sequences that chain agents/tools into
  a single automation, executed through the existing agent/tool layer
- a `Workflow` + `WorkflowRun` (or equivalent) model + repository persisting a
  schedule/trigger definition and each execution's outcome for an audit trail
- REST: list/create/update/delete workflows, enable/disable a schedule, run a
  workflow on demand, and read workflow-run status/history
- destructive steps in an automation continue to route through the Stage 4.5
  confirmation flow and are always logged

Frontend:

- an automation view: define a workflow (schedule/trigger + steps), enable or
  disable it, run it on demand, and review past workflow runs (read-only)

---

# Architecture Contract

- **Automation → Agent/Service → Integration** — automations start agent runs or
  tool chains; they must never reference integrations directly, and integrations
  must never contain business logic.
- **Reuse, don't fork** — the scheduler drives the existing `AgentService` /
  `AgentRunner` and `ToolRegistry`; the agent loop, the chat tool-use loop, and
  the Stage 4.5 confirmation flow are reused unchanged.
- **Auditability** — every scheduled/triggered run persists its outcome (and any
  destructive action) to the audit trail, reusing the Stage 6 `AgentRun` trail
  where an automation runs an agent.
- **Graceful degradation** — a workflow reports a clear failure for a step when a
  required service/provider is unavailable rather than crashing the scheduler or
  the app.

---

# Restrictions

DO NOT implement:

- PostgreSQL / Redis / Docker / horizontal scaling / production deploy — Stage 8
- new external integrations beyond what Stages 2–4.5 already provide
- changes to the Stage 4.5 confirmation mechanics or the Stage 5 retrieval core
- changes to the Stage 6 agent contract beyond how automations invoke it
- voice changes — Stage 4.7 is complete

Do not implement future stages beyond Stage 7.

---

# Deliverables

- a scheduling layer that starts agent runs / tool chains on a schedule
- event-driven triggers that start automations from internal events
- a workflow composer: named, persisted tool/agent sequences
- a `Workflow` + `WorkflowRun` model + repository (definition + outcome trail)
- REST endpoints to manage workflows, control schedules, run on demand, and read
  run history
- an automation UI: define, enable/disable, run, and review workflows

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
Scheduled execution — the scheduling layer + `Workflow` / `WorkflowRun` model +
repository, starting an agent run or a single tool chain on a schedule, with
REST + a minimal UI to define, enable/disable, run on demand, and view runs.

Major Feature 2:
The workflow composer (multi-step sequences) + event-driven triggers, plus the
workflow run-history + step-visibility UI.

After each major feature:

- explain decisions
- list files created / modified
- wait for approval

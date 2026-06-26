# Stage 6 Summary — Agents

**Status:** Complete
**Outcome:** Personal OS now has an **agent layer**. Domain agents orchestrate
the existing service layer into **autonomous multi-step workflows**, composing
the Stage 4 read tools and Stage 4.5 write tools in a **plan → act → observe**
loop — without per-step user prompting. Every run is recorded to an `AgentRun`
audit trail (plan, each tool call and the result it observed, and the final
outcome), so an agent's reasoning and any destructive action it proposes are
fully inspectable after the fact. Agents act **only through the shared
`ToolRegistry`** (Agent → Service → Integration); they never touch integrations
directly and introduce **no new side-effect path** — the Stage 4.5 confirmation
flow and Stage 5 `search_knowledge` are reused unchanged.

This was a backend-plus-frontend stage delivered in two major features:

- **Major Feature 1 — the agent framework** (commit `d4ede93`): the base `Agent`
  interface + `AgentContext`, the `AgentRunner` that records each step, the
  `AgentRegistry`, the `AgentRun` + `AgentStep` models and repository, the
  `AgentService` facade + REST endpoints, and the `StudyAgent` reference agent
  end-to-end with a minimal UI.
- **Major Feature 2 — domain agents + run inspection** (commit `62ba18b`): the
  `EmailAgent`, `CalendarAgent`, and `NotificationAgent`, plus a run-history and
  step-visibility UI (select any past run to see its full step trail).

> No scheduled workflows, event-driven triggers, or a workflow composer were
> introduced (Stage 7); no PostgreSQL/Redis/Docker (Stage 8). The Stage 5
> retrieval core and the Stage 4.5 confirmation mechanics are reused as-is.

---

## Objectives Completed

- **Agent framework** — a base `Agent` (key/name/description/parameters + a
  `run(ctx)` workflow and an optional `plan(ctx)`) and an `AgentContext` exposing
  `param(...)` (read run inputs) and `act(tool, args, title=...)` (invoke a tool,
  record the observed result as one step, return it). The framework is
  deterministic: it composes tool calls rather than relying on a live LLM, so
  runs are reproducible and testable offline.
- **Agent runner + audit trail** — `AgentRunner` opens an `AgentRun`, records the
  plan, drives the loop (each tool call persisted as it happens), then records the
  result and marks the run `completed`; an exception is caught and recorded as an
  `error` step with the run marked `failed`. Steps persist incrementally, so
  partial progress survives a failure.
- **Domain agents** — four agents, each orchestrating services through tools:
  - `StudyAgent` (Study Briefing): schedule + knowledge → autonomous study task.
  - `EmailAgent` (Inbox Triage): unread mail → autonomous follow-up task.
  - `CalendarAgent` (Meeting Prep): schedule + knowledge prep notes → autonomous
    prep task.
  - `NotificationAgent` (Daily Digest): unread mail + events + notifications →
    **proposes** a Telegram digest, which routes through the confirmation flow as
    a pending action (the auditable destructive-action path).
- **REST** — `GET /agents` (catalogue), `POST /agents/{key}/runs` (start a run),
  `GET /agents/runs` (history), `GET /agents/runs/{id}` (run + steps). All reads
  owner-scoped.
- **Frontend** — an Agents page: a catalogue with per-agent trigger forms, a live
  step timeline for the latest run, and a selectable run history that fetches any
  past run's full plan → act → observe trail on demand.
- **Graceful degradation** — an unavailable tool/service produces a `failed`
  action step (clear in the trail) while the run as a whole still completes;
  a raising agent yields a recorded `error` step and a `failed` run rather than
  crashing the request.

---

## Files Created

**Major Feature 1**

- `backend/models/agent_run.py` (`AgentRun`, `AgentStep` + status/kind constants)
- `backend/repositories/agent_run_repository.py`
- `backend/agents/{__init__,base,runner,registry,study_agent}.py`
- `backend/schemas/agent.py`
- `backend/services/agent_service.py`
- `backend/api/routes/agents.py`
- `backend/tests/test_stage6_agents.py`
- `frontend/src/features/agents/{api.ts,useAgents.ts,format.ts}`
- `frontend/src/features/agents/components/{AgentCard,AgentRunSteps,AgentRunView,RunHistory}.tsx`
- `frontend/src/pages/AgentsPage.tsx`

**Major Feature 2**

- `backend/agents/{email_agent,calendar_agent,notification_agent}.py`

**Docs**

- `docs/stage-6-summary.md` — this file

## Files Modified

- `backend/models/__init__.py` — register `AgentRun` / `AgentStep`
- `backend/services/factory.py` — `build_agent_service` (agent registry + runner +
  user-scoped tool registry wired with the confirmation flow and knowledge search)
- `backend/api/dependencies.py` — `get_agent_service`
- `backend/api/routes/__init__.py` — mount the agents router
- `backend/agents/registry.py` — register all four agents (MF2)
- `backend/tests/test_stage6_agents.py` — extend with the MF2 agents (MF2)
- `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx` — Agents
  route + nav entry
- `frontend/src/features/agents/useAgents.ts` — `useAgentRun` (run detail) (MF2)
- `frontend/src/features/agents/components/RunHistory.tsx` — selectable runs (MF2)
- `frontend/src/pages/AgentsPage.tsx` — selected-run step visibility (MF2)
- `CURRENT_SPRINT.md` — Stage 6 spec, then advanced to Stage 7

---

## Architectural Decisions

- **Agents are a layer above services, not a rewrite of the chat core.** They
  drive the same user-scoped `ToolRegistry` the chat loop uses; the AIService,
  ConfirmationService, and ToolExecutor are untouched.
- **Deterministic orchestration over LLM planning.** Agents compose an explicit
  tool sequence rather than delegating planning to a provider. This makes every
  run auditable and testable with no network/SDK, and is what lets the whole
  agent suite run offline. The LLM remains available to agents that need
  synthesis, but the framework does not depend on it.
- **Reduced confirmation, not no confirmation.** Per the sprint contract, agents
  run autonomously where it is safe — `create` actions (e.g. `create_task`)
  execute immediately. Destructive/outbound actions (Telegram send, email,
  calendar/event deletes) still route through the existing confirmation flow as
  **pending actions**: logged to the audit trail *and* held for approval. This is
  deliberately safer than the roadmap's "bypass interactive confirmation" note —
  autonomy is applied to creates, while irreversible outbound effects remain
  user-gated, and the agent step records that they await approval.
- **Steps as a child table.** `AgentStep` rows (mirroring `Document`/
  `DocumentChunk`) give a queryable, ordered trail and let partial progress
  persist if a later step fails.
- **Synchronous execution.** A run is fully recorded by the time the start
  endpoint returns; background execution is deferred to Stage 7 (scheduling).
- **Graceful degradation as a first-class outcome.** A missing tool or
  unavailable service becomes a `failed` step (not an exception); the run
  completes and the failure is visible in the trail.

---

## Verification

- `ruff check backend/agents backend/tests/test_stage6_agents.py …` — passes
- `python -m pytest backend/tests/` — **128 passed** (12 Stage 6 tests + prior
  116), all offline (no LLM, network, or SDKs)
- Frontend `tsc -b`, `vite build`, and `eslint` — all clean
- Live HTTP smoke (TestClient): all four agents complete; step trails persist and
  are returned by the run-detail endpoint; the `NotificationAgent` digest produces
  exactly one `send_telegram_message` pending action (confirmation/audit path)

---

## Unresolved Issues / Technical Debt

- **Synchronous, non-cancellable runs.** A run executes inline in the request and
  cannot be cancelled or resumed; long chains would benefit from the background
  execution that arrives with Stage 7 scheduling.
- **No live step streaming.** Steps are persisted as they happen, but the UI
  receives them when the run returns (or on history refetch) rather than over
  SSE/WebSocket; the chat SSE pattern could be applied later.
- **Deterministic plans, not adaptive.** Agents follow a fixed tool sequence;
  they do not yet branch on observations or use the LLM to decide next steps.
- **Action-type policy is global.** Autonomy is decided by the shared
  `ConfirmationService` policy (creates autonomous; updates/deletes/outbound
  confirmed); there is no per-agent autonomy override yet.
- **Outbound effects depend on prior configuration.** Agents that propose email/
  Telegram/calendar writes still rely on Stage 2/3 setup; without it the proposal
  is recorded but execution on approval reports the capability as unconfigured.
- **Single-user scoping.** Runs are owner-scoped like the rest of the app;
  per-user isolation waits on an auth stage.

---

## Recommendations for Stage 7 (Automation)

- Add a scheduler layer (APScheduler is already a dependency) that can **start
  agent runs on a schedule or trigger**, reusing `AgentService`/`AgentRunner`
  unchanged — the runner is already self-contained and synchronous.
- Introduce a **workflow composer** that chains agents/tools into named
  sequences; the `AgentRun`/`AgentStep` trail is a natural substrate for
  recording composed runs.
- Add **event-driven triggers** (e.g. on new email → run `EmailAgent`); keep the
  Agent → Service → Integration contract and route any destructive step through
  the existing confirmation/audit path.
- Consider **background execution + live step streaming** (SSE) so scheduled and
  long-running agent runs surface progress without blocking a request.
- Keep the modular-monolith boundaries: automation is a new orchestration layer
  above agents, not a change to the agent or chat cores.

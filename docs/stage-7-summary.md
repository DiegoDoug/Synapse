# Stage 7 Summary: Automation Layer

## Objectives Completed

1. **Scheduled workflow execution** — workflows run on interval, cron (daily at HH:MM UTC), event, or manual triggers via APScheduler.
2. **Personalized schedule settings** — users choose when and how often a workflow runs (`interval_minutes`, `cron_hour`/`cron_minute`) and how many times it may run before auto-disabling (`max_runs` + `run_count` cap).
3. **Event-driven triggers** — workflows react to `new_email`, `new_calendar_event`, and `new_notification` data; a monotonic cursor prevents replaying events that existed before the trigger was enabled.
4. **Multi-step workflow composer** — users build ordered sequences of agent and tool steps; each step exposes its own parameter inputs; steps can be reordered and removed.
5. **Catalogue endpoint** — `GET /workflows/catalogue` advertises available agents, tools, and event types so the frontend composer stays in sync with the backend.
6. **Step-visibility trail** — every workflow run records a per-step `WorkflowRunStep` outcome; the UI shows which step succeeded or failed and why.
7. **Automation UI** — full CRUD, enable/disable, run-on-demand, and run-history with per-step trail on the `/automation` page.

---

## Files Created

### Backend
- `backend/models/workflow.py` — `Workflow`, `WorkflowRun`, `WorkflowStep`, `WorkflowRunStep` SQLModel tables; schedule constants; `STEP_AGENT`, `STEP_TOOL`, `SCHEDULE_EVENT` constants.
- `backend/repositories/workflow_repository.py` — CRUD for all four models; cascade delete; step CRUD (`list_steps`, `replace_steps`); run-step CRUD; `list_enabled_events()`.
- `backend/schemas/workflow.py` — `WorkflowCreate`, `WorkflowUpdate`, `WorkflowRead`, `WorkflowRunRead`, `WorkflowStepInput`, `WorkflowStepRead`, `WorkflowRunStepRead`, `CatalogueEntry`, `CatalogueEvent`, `CatalogueParam`, `WorkflowCatalogue`.
- `backend/services/workflow_scheduler.py` — `WorkflowScheduler` wrapping APScheduler; `sync(workflow)` builds `IntervalTrigger` or `CronTrigger`; process-level `set/get_workflow_scheduler()` singleton.
- `backend/services/workflow_service.py` — `WorkflowService` orchestrating CRUD, scheduling, execution (`_run_sequence` fail-fast), catalogue, and event evaluation; reuses `AgentService` and `ToolRegistry` without forking.
- `backend/services/workflow_events.py` — event type constants; `current_mark(session, user_id, event_type)` reads max row id from email/calendar/notification repos.
- `backend/tasks/workflow_tasks.py` — `run_scheduled_workflow(workflow_id)` and `evaluate_workflow_events()` best-effort tasks.
- `backend/api/routes/workflows.py` — 10 REST endpoints: list, create, catalogue, get, update, delete, enable, disable, run, runs.
- `backend/tests/test_stage7_workflows.py` — 22 tests (13 MF1 + 9 MF2); `_FakeScheduler` for scheduler assertions; covers multi-step sequences, tool steps, fail-fast, catalogue, event arming/firing, and cap auto-disable.

### Frontend
- `frontend/src/features/workflows/api.ts` — DTO types + all API fetchers including `fetchCatalogue()`.
- `frontend/src/features/workflows/format.ts` — `runStatusMeta`, `scheduleKindLabel`, `scheduleSummary`, `eventLabel`, `stepsSummary`, `runCapSummary`, `formatDateTime`.
- `frontend/src/features/workflows/useWorkflows.ts` — React Query hooks; `useWorkflowCatalogue` with 5-min staleTime.
- `frontend/src/features/workflows/schedule.ts` — `ScheduleDraft` interface; `draftIntervalMinutes` helper.
- `frontend/src/features/workflows/components/ScheduleEditor.tsx` — 4-mode picker, interval frequency inputs, time picker, event-type dropdown, run-cap input.
- `frontend/src/features/workflows/components/StepEditor.tsx` — ordered composer; agent/tool optgroup selector; per-step param inputs; ArrowUp/Down/Trash2 controls.
- `frontend/src/features/workflows/components/WorkflowForm.tsx` — integrates `StepEditor` + `ScheduleEditor`; seeds from existing workflow on edit.
- `frontend/src/features/workflows/components/WorkflowCard.tsx` — schedule summary row including `stepsSummary`; Zap icon for event schedules.
- `frontend/src/features/workflows/components/WorkflowRunHistory.tsx` — per-step trail with `StepRow`; status chips; error/result detail.
- `frontend/src/pages/AutomationPage.tsx` — full automation page with workflow list, create/edit panel, run-history panel.

---

## Files Modified

### Backend
- `backend/models/__init__.py` — added `WorkflowStep`, `WorkflowRunStep` imports.
- `backend/services/factory.py` — `build_workflow_service` constructs `ToolRegistry` + `AgentService` + `WorkflowScheduler` and injects them into `WorkflowService`.
- `backend/api/dependencies.py` — added `get_workflow_service` dependency provider.
- `backend/api/routes/__init__.py` — included `workflows_router`.
- `backend/scheduler.py` — bootstraps `WorkflowScheduler` singleton on startup; registers `workflow-events` interval job.
- `backend/main.py` — clears `WorkflowScheduler` singleton on shutdown.
- `backend/config.py` — added `workflow_event_poll_minutes: int = 2`.
- `backend/repositories/email_repository.py` — added `max_id_for_accounts`.
- `backend/repositories/calendar_repository.py` — added `max_id_for_accounts`.
- `backend/repositories/notification_repository.py` — added `max_id_for_user`.
- `backend/tests/test_stage3_telegram.py` — updated expected APScheduler job sets to include `"workflow-events"`.

### Frontend
- `frontend/src/App.tsx` — added `AutomationPage` import + `/automation` route.
- `frontend/src/components/layout/Sidebar.tsx` — added `Workflow` icon + `/automation` nav item.
- `frontend/src/api/client.ts` — added `apiPatch<T>` function.

---

## Architectural Decisions

1. **Automation → Agent/Service → Integration contract preserved** — `WorkflowService` invokes `AgentService` and `ToolRegistry`; no workflow code touches integrations directly.
2. **APScheduler reuse** — the existing Stage 3 scheduler instance is extended with per-workflow jobs; no new scheduler process or broker.
3. **Singleton scheduler pattern** — `set/get_workflow_scheduler()` lets request handlers sync jobs with the process-level scheduler without circular imports.
4. **Monotonic event cursor** — on first enable, the cursor is set to the current max row id (`_arm_if_event`), so only data synced after activation fires the workflow; prevents backlog flooding.
5. **Fail-fast multi-step execution** — `_run_sequence` stops at the first failed step and records the failure; subsequent steps are not attempted.
6. **Step-visibility without duplicating AgentRun** — `WorkflowRunStep` links to the `AgentRun` id for agent steps rather than copying the trail.
7. **Lazy task import** — `run_scheduled_workflow` is imported inside `WorkflowScheduler.sync()` to break the factory → tasks → scheduler cycle.
8. **Legacy single-step backward compatibility** — MF1 workflows with `agent_key`/`params` columns (no `WorkflowStep` rows) are handled by `_legacy_steps()` so existing data survives the MF2 migration.

---

## Unresolved Issues

- None. All 22 backend tests pass; `tsc`, `vite build`, `ruff`, and `eslint` are clean.

---

## Technical Debt

- `WorkflowScheduler.sync()` rebuilds the APScheduler job on every `PATCH` even if the schedule is unchanged; a diff-check would reduce scheduler churn.
- The `workflow-events` poll interval is a single global config value (`workflow_event_poll_minutes`); per-event-type granularity may be desirable as event volume grows.
- `_run_tool_step()` detects errors via string prefix matching (`result.startswith(("Unknown tool:", "Tool '"))`); a structured error return from `ToolRegistry.execute` would be cleaner.

---

## Recommendations for Stage 8

- Migrate SQLite to PostgreSQL; `WorkflowRun` and `WorkflowRunStep` will benefit most from proper indexing and concurrent writes.
- Move `run_scheduled_workflow` and `evaluate_workflow_events` to a Celery or ARQ task queue backed by Redis; APScheduler in-process is sufficient for single-node but doesn't survive worker restarts gracefully.
- Add a WebSocket or SSE push for live workflow run status so the UI updates without polling.
- Docker Compose the full stack (API, frontend, task worker, Redis, PostgreSQL) for reproducible deployment.

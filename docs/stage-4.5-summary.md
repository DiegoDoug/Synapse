# Stage 4.5 Summary — AI Actions

**Status:** Complete
**Outcome:** Personal OS's AI assistant is now **action-capable**. On top of the
Stage 4 read-only tool-use loop, it can perform internal CRUD (tasks, widget
config) and external/outbound writes (Gmail, Google Calendar, Telegram) and fill
& submit web forms — all gated by a confirmation system. Reads and internal
*creates* run autonomously; every update, delete, and outbound action is proposed
as a `PendingAction` the user must approve before it executes. It builds directly
on the Stage 4 `AIService` + `ToolRegistry`, the Stage 2 OAuth/sync services, the
Stage 3 Telegram delivery, and the ARCHITECTURE.md Service → Integration contract.

This is a backend-plus-frontend stage. No agents, voice, RAG/embeddings, or
scheduled automation were introduced (deferred to Stages 6 / 4.7 / 5 / 7).

Stage 4.5 was delivered in two major features on the `feature/ai-actions` branch
(merged via PR #16), gated by a new GitHub Actions CI workflow:

- **Major Feature 1 — confirmation flow + internal write tools** (commit
  `464c995`): `Task` + `PendingAction` models, `TaskService`, `WidgetService`,
  `ToolExecutor`, `ConfirmationService`, internal write tools, `/tasks` +
  `/actions` routes, and a `ConfirmationModal` surfacing proposals in the chat UI.
- **Major Feature 2 — external + browser write tools** (commit `ec56d48`):
  Gmail/Calendar/Browser integration writes, `EmailService`/`CalendarService`
  write methods, a `MessagingService`, the external + browser-write tools, and
  the `requires_confirmation` override that keeps all outbound actions confirmed.
- **CI** (commit `4fed081`): backend (ruff + pytest) and frontend (build + lint)
  jobs on every PR and push to `main`.

---

## Objectives Completed

- **`PendingAction` model + `ConfirmationService`** — a DB-backed proposal with a
  lifecycle (`pending → approved → executed/failed`, or `rejected`). The service
  owns the autonomous-vs-confirm decision and the approve/reject API, and tracks
  proposals raised during the current turn for SSE/result surfacing.
- **`ToolExecutor`** — the single execution path for every write, autonomous or
  approved. It dispatches a tool name + payload to the owning service method,
  resolves the target Google account, and wraps all execution so a failure becomes
  a `failed` action rather than an exception.
- **Internal write tools** — `create_task` (autonomous), `update_task`,
  `delete_task`, `update_widget_config` (confirmed), behind the existing
  `ToolRegistry`.
- **External write tools** — `send_email`, `create_calendar_event`,
  `delete_calendar_event`, `send_telegram_message`, all always confirmed
  (outbound is never autonomous).
- **Browser write + reads** — `BrowserService` gained `fill_and_submit` (one
  confirmed fill+submit operation), plus read-only `extract_structured_data` and
  `screenshot`; the `fill_form` / `extract_structured_data` / `take_screenshot`
  tools wrap them. Playwright stays lazy and degrades gracefully when absent.
- **AIService integration** — binds the turn's conversation to the
  `ConfirmationService` and surfaces proposals on `ChatResult.pending_actions`
  and as a `pending_action` SSE event.
- **API** — `GET/POST/PATCH/DELETE /tasks`, `GET /actions`,
  `POST /actions/{id}/approve`, `POST /actions/{id}/reject`.
- **Frontend** — a `ConfirmationModal` (generic over any pending action) and
  actions hooks (list pending, approve, reject); the Assistant page refreshes the
  pending queue on `pending_action` events and prompts for approval.
- **CI** — automated lint + test gating for backend and frontend.

---

## Files Created

**Major Feature 1**

- `backend/models/task.py`, `backend/models/pending_action.py` — new tables
- `backend/repositories/{task_repository,widget_repository,pending_action_repository}.py`
- `backend/services/{task_service,widget_service,tool_executor,confirmation_service}.py`
- `backend/services/tools/write_tools.py` — internal write tools
- `backend/schemas/{task,action}.py` — task + pending-action DTOs
- `backend/api/routes/{tasks,actions}.py`
- `backend/tests/test_stage45_actions.py`
- `frontend/src/features/actions/{api.ts,useActions.ts}`
- `frontend/src/components/ai/ConfirmationModal.tsx`

**Major Feature 2**

- `backend/services/messaging_service.py` — Telegram sends
- `backend/tests/test_stage45_external.py`

**CI / Docs**

- `.github/workflows/ci.yml`
- `docs/stage-4.5-summary.md` — this file

## Files Modified

- `backend/models/__init__.py` — register `Task`, `PendingAction`
- `backend/models/dashboard_widget.py` — `config` JSON column
- `backend/integrations/google/gmail.py` — `send_message`
- `backend/integrations/google/calendar.py` — `create_event` / `delete_event`
- `backend/integrations/browser/service.py` — `extract_structured_data`,
  `screenshot`, `fill_and_submit`
- `backend/services/email_service.py` — `send_email` (MIME assembly)
- `backend/services/calendar_service.py` — `create_event` / `delete_event`
- `backend/services/ai_service.py` — confirmation binding, pending-action
  surfacing, updated system prompt
- `backend/services/confirmation_service.py` — honor `requires_confirmation`
- `backend/services/tool_executor.py` — external + browser handlers, optional
  deps, account resolution, top-level safety
- `backend/services/tools/base.py` — `ToolContext.confirmations`
- `backend/services/tools/web_tools.py` — browser read tools
- `backend/services/factory.py` — wire executor / confirmation / write tools and
  external services from settings
- `backend/schemas/ai.py` — `pending_actions` on `ChatResult`
- `backend/schemas/action.py` — `ProposedAction.requires_confirmation`
- `backend/api/dependencies.py` — task + confirmation service providers
- `backend/api/routes/__init__.py` — mount tasks / actions routers
- `backend/config.py` — Google scopes now include `gmail.send` + `calendar.events`
- `frontend/src/features/ai/{api.ts,useAssistant.ts}` — `pending_action` event
- `frontend/src/pages/AssistantPage.tsx` — render the confirmation modal
- `CURRENT_SPRINT.md` — Stage 4.5 spec, then advanced to Stage 4.7

---

## Architectural Decisions

- **One execution path.** Every write — autonomous create or approved
  update/delete/outbound — runs through `ToolExecutor`, which calls only services
  (never repositories or integrations directly), preserving the
  Service → Integration contract.
- **Confirmation policy lives in the service, not the tools.** `ConfirmationService`
  decides autonomous-vs-confirm. Internal creates are autonomous; updates/deletes
  confirm. A `ProposedAction.requires_confirmation` override lets external/browser
  tools force confirmation regardless of `action_type` — **outbound actions are
  never autonomous**, since an email can't be unsent.
- **Tools never mutate.** Write tools build a `ProposedAction` and hand it to the
  `ConfirmationService`; they hold no business logic, mirroring the read-tool
  pattern.
- **Per-request `ConfirmationService` shared with the AIService.** The factory
  builds one instance backing both the write tools (via `ToolContext`) and the
  service, so proposals raised mid-turn are visible to the response and SSE
  stream without extra queries.
- **Single confirmed fill+submit.** `BrowserService` is stateless (open → act →
  close per call), so splitting fill and submit across confirmation boundaries
  would lose the page session. `fill_and_submit` is one confirmed operation —
  faithful to "fill_form + submit (with confirmation)" and actually executable.
- **Execution never raises.** `ToolExecutor.execute` wraps handlers in a
  top-level guard; a failure becomes a `failed` `PendingAction` with the reason,
  never an exception out of `approve`.
- **Optional capabilities degrade.** External services are wired from settings;
  when Google/Telegram/Playwright are absent the handler returns a clean failure
  at execution time rather than failing construction — same philosophy as Stage 4
  `web_fetch`.
- **Generic confirmation UI.** The `ConfirmationModal` renders any
  `PendingActionDto`, so external/browser proposals surfaced with zero
  extra frontend work.

---

## Verification

- `ruff check backend/` — passes
- `python -m pytest backend/tests/` — **73 passed** (15 new Stage 4.5 tests +
  prior 58)
- Confirmation routing, executor dispatch, approve/reject, ownership scoping,
  graceful failure when unconfigured, and browser degradation all exercised with
  in-memory fakes — no network, OAuth, or Playwright in tests
- Frontend `tsc -b`, `vite build`, and `eslint` all clean
- CI (GitHub Actions) green on PR #16 for both backend and frontend jobs

---

## Unresolved Issues / Technical Debt

- **No live external-write verification.** Gmail send, Calendar create/delete, and
  Telegram send are implemented to spec and tested with fakes, but not exercised
  against real credentials here; first real send should be smoke-tested manually.
- **OAuth re-consent required.** Default Google scopes now include `gmail.send`
  and `calendar.events`; accounts connected before this stage must reconnect to
  grant write access.
- **`take_screenshot` is text-only.** It captures the PNG but returns a textual
  confirmation (size/format), not the image. Feeding pixels into model context
  needs a multimodal tool-result contract change across all providers — deferred.
- **Stateless browser writes.** `fill_and_submit` runs in a single page session;
  multi-page flows (login → navigate → submit) are out of scope until a
  persistent browser session exists (relevant to Stage 7 automation).
- **Single-user scoping.** Tasks, widgets, and pending actions scope to the one
  owner user via `get_current_user_id`; real per-user isolation waits on an auth
  stage.
- **Account resolution picks the first Google account.** External writes target
  the user's first connected Google account; explicit account selection is a
  future refinement once multiple accounts are common.

---

## Recommendations for Stage 4.7 (Voice Interface)

- Add a **`STTService`** (faster-whisper) and **`TTSService`** (Kokoro) in the
  service layer, model loaded at startup, streaming audio chunks — keep the
  Route → Service → Integration contract.
- Add a **`/voice/transcribe`** + **`/voice/synthesize`** REST path for
  push-to-talk, injecting the transcript into the existing AI chat flow so voice
  reuses the Stage 4/4.5 tool-use + confirmation loop unchanged.
- Add a **`WakeWordService`** (openWakeWord) behind a `/ws/voice` WebSocket for
  the opt-in wake-word mode; keep it server-side and toggled off by default.
- Frontend: a `VoiceButton` (push-to-talk + waveform), an `AudioStreamer`
  (AudioWorklet → PCM over WebSocket), a `useVoice` state machine, and a
  `VoiceSettings` panel (model size, voice, wake-word toggle).
- Keep the synchronous service pattern; load heavy models lazily so the app still
  boots when the voice dependencies aren't installed (mirror Playwright/SDK
  graceful degradation).

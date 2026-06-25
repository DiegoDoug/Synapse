# Stage 4 Summary — AI Layer

**Status:** Complete
**Outcome:** Personal OS now has a working AI assistant. It routes chat to a
configurable LLM provider (Anthropic primary, OpenAI secondary, Ollama local),
persists conversations, runs a read-only tool-use loop over the user's synced
data and the web, and streams replies to the UI over SSE. It builds directly on
the Stage 2 sync services, the Stage 3 notification center, and the
ARCHITECTURE.md Service → Integration contract.

This is a backend-plus-frontend stage. Everything is **read-only**: no write
tools, confirmations, voice, RAG/embeddings, agents, or automation were
introduced (deferred to Stages 4.5 / 4.7 / 5 / 6 / 7).

Stage 4 was delivered in two major features on the `feature/ai-layer` branch:

- **Major Feature 1 — AI foundation** (commit `d2c5bbb`): provider abstraction
  + routing, prompt system, `AIService` + `ConversationService`, conversation
  models, typed REST endpoints, and an Assistant chat UI (no tools yet).
- **Major Feature 2 — tools & streaming** (commit `4a076c7`): `ToolRegistry`
  with read-only tools, the tool-use loop, a read-only `BrowserService`
  (Playwright), SSE streaming, and tool-call surfacing in the UI.

---

## Objectives Completed

- **Provider abstraction** — an `LLMProvider` interface in the Integration layer
  with interchangeable `AnthropicProvider`, `OpenAIProvider`, and
  `OllamaProvider`. A new provider is one file plus one factory arm. SDKs are
  lazy-imported so the app boots with none installed/configured.
- **Provider-neutral contract** — `ChatMessage` / `ChatResponse` DTOs normalize
  every vendor. `ChatResponse.metadata` is an open bag for provider diagnostics
  (token usage, stop/finish reasons) with no future DTO churn.
- **AIService** — provider selection, system-prompt assembly, the bounded
  tool-use loop, and both a non-streaming and an SSE streaming path. Exposes
  `health()` for diagnostics. Providers are never imported by routes.
- **ConversationService + models** — `Conversation`, `Message`, and
  `SystemPrompt` (named to disambiguate future prompt templates / tool / agent
  prompts), with user-scoped persistence and read views.
- **ToolRegistry + read-only tools** — `search_emails`, `get_calendar_events`,
  `get_notifications` (aggregated across the user's accounts), and `web_fetch`,
  each mapping a name + JSON schema to an existing read path. Built per request,
  bound to the session + user, strictly read-only.
- **BrowserService** — headless, read-only Playwright wrapper (navigate URL +
  extract text), lazy-imported and degrading gracefully when absent.
- **API** — `POST /ai/chat`, `POST /ai/chat/stream` (SSE), `GET /ai/health`,
  `GET/POST /conversations`, `GET /conversations/{id}`, `GET /prompts`, all
  typed with clean provider-error mapping.
- **Frontend** — an Assistant page (streaming chat, conversation sidebar, prompt
  selector, live provider indicator, tool-call source chips) and an "Ask
  Personal OS" command bar that routes typed input to the AI service.

---

## Files Created

**Major Feature 1**

- `backend/models/conversation.py`, `backend/models/message.py`,
  `backend/models/system_prompt.py` — chat tables
- `backend/schemas/ai.py` — provider-neutral + API DTOs
- `backend/integrations/ai/{__init__,base,anthropic_provider,openai_provider,ollama_provider}.py`
  — `LLMProvider` + the three thin clients
- `backend/services/ai_service.py`, `backend/services/conversation_service.py`
- `backend/repositories/conversation_repository.py`,
  `backend/repositories/system_prompt_repository.py`
- `backend/api/routes/ai.py`, `backend/api/routes/conversations.py`,
  `backend/api/routes/prompts.py`
- `backend/tests/test_stage4_ai.py` — provider routing, chat, persistence
- `frontend/src/features/ai/{api.ts,useAssistant.ts}`
- `frontend/src/components/ai/{ChatInput,ChatMessage,ConversationSidebar,PromptSelector,ProviderIndicator,CommandBar}.tsx`
- `frontend/src/pages/AssistantPage.tsx`

**Major Feature 2**

- `backend/integrations/browser/{__init__,service}.py` — read-only
  `BrowserService`
- `backend/services/tools/{__init__,base,registry,read_tools,web_tools}.py` —
  `Tool`, `ToolContext`, `ToolRegistry`, and the read-only tools
- `backend/tests/test_stage4_tools.py` — tools, tool-use loop, streaming
- `frontend/src/components/ai/ToolCallChip.tsx` — tool/source chip

**Docs**

- `docs/stage-4-summary.md` — this file

## Files Modified

- `backend/models/__init__.py` — register `Conversation`, `Message`,
  `SystemPrompt`
- `backend/integrations/ai/base.py` + all three providers — `tools` on `chat()`,
  `stream_chat()`, `supports_tools` (MF2)
- `backend/schemas/ai.py` — tool DTOs + `tool_calls` on `ChatResponse`/`ChatResult`
- `backend/services/ai_service.py` — tool-use loop + streaming (MF2)
- `backend/services/interfaces.py` — `AIServiceInterface`,
  `ConversationServiceInterface`
- `backend/services/factory.py` — provider, conversation, tool-registry, and
  AI-service builders
- `backend/api/dependencies.py` — AI + conversation service providers
- `backend/api/routes/__init__.py` — mount ai / conversations / prompts routers
- `backend/api/routes/ai.py` — SSE streaming endpoint (MF2)
- `backend/config.py` / `backend/.env.example` — multi-provider AI settings
- `backend/requirements.txt` — anthropic, openai, playwright
- `frontend/src/App.tsx` — `/assistant` route
- `frontend/src/components/layout/Sidebar.tsx` — Assistant nav entry
- `frontend/src/components/layout/Header.tsx` — "Ask Personal OS" command bar
- `CURRENT_SPRINT.md` — Stage 4 spec, then advanced to Stage 4.5

---

## Architectural Decisions

- **Route → Service → Provider, enforced.** Routes depend on `AIService` only;
  providers live in the Integration layer and are never imported by routes. The
  `LLMProvider` interface is the single swap point.
- **Providers mapped to the Integration layer, not a new `app/ai/` tree.** The
  task brief sketched `backend/app/ai/...`; the repo uses a flat `backend/`
  layout, so providers went to `integrations/ai/` per ARCHITECTURE.md. Intent
  preserved, conventions respected.
- **Synchronous, threadpool-friendly service layer.** Provider calls are sync to
  match the existing email/calendar/notification services; streaming adds a
  generator path without an async DB rewrite.
- **Open `metadata` on `ChatResponse`.** Provider-specific diagnostics flow
  through to the API/UI without DTO changes (an explicit Stage 4 adjustment).
- **`SystemPrompt`, not `Prompt`.** Renamed to disambiguate from future prompt
  templates, tool prompts, and agent prompts.
- **`health()` + endpoint.** `GET /ai/health` reports active provider, model,
  and availability for diagnostics, settings, and future provider switching.
- **Read-only tools mapped to existing reads.** The `ToolRegistry` binds tool
  names to repository reads per request (user + session scoped); no tool writes.
  A single failing tool returns text, never breaking the loop.
- **Anthropic primary for tool use.** Anthropic and OpenAI translate native
  tool-use/function-calling; Ollama streams but stays tool-less (local tool
  support varies). The `tools` argument is accepted everywhere for parity.
- **Tool steps persisted as `role="tool"` messages.** Reopened threads show
  their sources; provider history is rebuilt from user/assistant turns only, so
  tool rows never corrupt the next prompt.
- **Streaming = chunked after tools, true streaming otherwise.** Tool resolution
  needs a non-streaming pass to parse calls, so the final answer is chunked when
  tools are available and token-streamed when they are not — avoiding a wasteful
  second model call on every turn.
- **Provider failures as SSE `error` events.** Once the stream has started, a
  provider error surfaces as an event, not an HTTP 500; the non-streaming path
  maps `ProviderError` to 503/429/502.
- **Graceful degradation.** With no API key the app still boots and
  `/ai/health` reports `available: false`; with Playwright absent `web_fetch`
  returns a friendly message instead of failing.

---

## Verification

- `ruff check backend` — passes
- `pytest backend` — 45 passed (11 MF1 AI + 11 MF2 tools/streaming + prior 23)
- SSE endpoint smoke-tested via `TestClient`: `200`, `text/event-stream`,
  emits a `conversation` event then a graceful `error` event when no key is set
- Tool-use loop, tool registry, read tools, and streaming exercised with
  in-memory fake providers — no network or SDK calls in tests
- Frontend `tsc -b`, `eslint`, and `vite build` all clean

---

## Unresolved Issues / Technical Debt

- **No live LLM verification.** Providers are implemented to spec and tested with
  fakes, but not exercised against real Anthropic/OpenAI keys or a running
  Ollama in this environment; first real call should be smoke-tested manually.
- **No live browser verification.** `BrowserService` is implemented to spec but
  not run against a real page here (Playwright browser provisioning is
  environment-managed); first `web_fetch` should be smoke-tested manually.
- **Tool history is display-only.** Persisted `role="tool"` rows are summaries
  for the UI; full tool I/O is reconstructed in-memory per turn and not replayed
  across turns (acceptable — tools are read-only and idempotent).
- **Chunked streaming when tools are available.** True token streaming only
  applies when no tools are advertised (e.g. Ollama). Real streamed tool-use
  would require provider streaming + incremental tool parsing (a later refinement).
- **Single-user scoping.** Conversations/tools scope to the one owner user via
  the existing `get_current_user_id`; real per-user isolation waits on an auth
  stage.
- **Plaintext key config.** API keys live in env config; encrypt-at-rest belongs
  with the Stage 8 production move.

---

## Recommendations for Stage 4.5 (AI Actions)

- Add **write tools** behind the existing `ToolRegistry`, reusing the read-tool
  pattern: internal CRUD (create/update/delete task, widget config) and external
  writes (send email, create/delete calendar event, send Telegram).
- Introduce a **`PendingAction` model + `ConfirmationService`**: reads and
  creates run autonomously; updates and deletes require user approval before
  execution (per ROADMAP Stage 4.5).
- Surface pending actions in the chat UI via a confirmation modal; stream
  approval state over the existing SSE channel / a `pending_action` event.
- Promote `BrowserService` to limited write (form fill + submit) **with
  confirmation**, keeping read navigation as-is.
- Keep the synchronous service/DB pattern and the Route → Service → Provider
  contract; the tool-use loop already has the hook points for confirmations.

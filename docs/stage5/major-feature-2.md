# Stage 5 — Major Feature 2: Semantic search + grounded answers (RAG)

**Status:** complete.

Major Feature 1 built the ingestion pipeline (the index). Major Feature 2 adds
the **read side**: semantic search over indexed chunks, exposed both as a REST
endpoint for a search UI and — more importantly — as a `search_knowledge` tool
the assistant calls inside the existing Stage 4 tool-use loop to **ground its
answers with citations**. No new write, agent, or confirmation logic is added;
grounding reuses the chat path unchanged (per `CURRENT_SPRINT.md`).

## What was built

### Backend

- **`KnowledgeService`** (`backend/services/knowledge_service.py`) — embeds the
  query, searches the vector store scoped to the user, and resolves matches back
  to their chunk text + source filename for citations. Returns `KnowledgeHit`s
  ordered best-first.
  - **Re-seed on demand**: when the in-process fallback store is used, the index
    lives only in memory and is empty after a restart while documents persist.
    `search` lazily rebuilds it from the embeddings stored on `DocumentChunk`
    rows (no re-embedding). No-op for external stores (Qdrant own their
    persistence). This consolidates the seeding logic that previously lived on
    `DocumentService` — search is its only consumer.
  - **Graceful degradation**: with embeddings uninstalled, `available()` is
    False and `search` returns `[]` instead of raising.
- **`search_knowledge` read tool** (`backend/services/tools/read_tools.py`) —
  a Stage-4-style read tool. Runs `KnowledgeService.search` and returns excerpts
  formatted with `[n]` citation markers + source filenames, instructing the
  model to cite as `[n]`. Reports unavailable instead of failing when the KB is
  off. Wired into the `ToolRegistry` via a new `knowledge` field on
  `ToolContext`; advertised only when a `KnowledgeService` is supplied.
- **System prompt** — `DEFAULT_SYSTEM_PROMPT` now tells the assistant it can
  search the knowledge base and should cite passages it uses as `[n]`.
- **REST** — `GET /knowledge/search?query=&limit=`
  (`backend/api/routes/knowledge.py`) → `KnowledgeSearchResponse`
  (`query`, `available`, `hits`). Backs the search UI; shares the index the tool
  reads.
- **Wiring** — `build_knowledge_service` factory, `get_knowledge_service`
  dependency, `build_tool_registry`/`build_ai_service` pass the knowledge service
  through, and the knowledge router is registered. The embedding model + vector
  store are the same process-cached singletons ingestion writes into, so search
  reads exactly what was indexed.

### Frontend

- **Knowledge search UI** (`features/documents/components/KnowledgeSearch.tsx`) —
  a search box + ranked results (source filename, % match, excerpt) using a
  `useKnowledgeSearch` mutation and the `searchKnowledge` API. Shown on the
  Knowledge Base page once at least one document is indexed; surfaces an
  "offline" hint when embeddings aren't installed.
- **Citations in chat** (`components/ai/ToolCallChip.tsx`) — knowledge-base
  retrievals render with a book icon and a "Knowledge base" label, so grounded
  answers visibly show the source the assistant cited. This reuses the existing
  tool-chip "source" rendering on the assistant page (live stream + persisted
  history), so no chat-core changes were needed.

## Architecture notes

- RAG **reuses the tool-use loop**: `search_knowledge` is a read tool exactly
  like the Stage 4 read tools. Grounding adds no write/agent/confirmation logic.
- Ingestion (`DocumentService`) and search (`KnowledgeService`) are separate
  services over a shared index, both talking to the embeddings + vector-store
  integrations through the integration seam.

## Tests

`backend/tests/test_stage5_knowledge.py` (8 tests) — relevance ordering,
user-scoping, unavailable/empty paths, re-seed after a simulated restart, the
`search_knowledge` tool (citation formatting, unavailable, no-results), route
registration, and the `GET /knowledge/search` REST flow — all with a
deterministic fake embedding. Full backend suite: **116 passed**, ruff clean.
Frontend typechecks, lints, and builds clean.

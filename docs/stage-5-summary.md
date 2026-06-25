# Stage 5 Summary — Knowledge System (RAG)

**Status:** Complete
**Outcome:** Personal OS now has a **personal knowledge base**. Upload documents
and they are extracted, chunked, embedded, and indexed; the assistant can then
**ground its answers** in them, citing the passages it used as `[n]`. Retrieval
is exposed as a `search_knowledge` read tool inside the existing Stage 4 tool-use
loop, so grounded answers reuse the chat path and the Stage 4.5 confirmation flow
**unchanged** — no new write, agent, or confirmation logic. Heavy dependencies
(sentence-transformers, Qdrant) are lazy and optional: the app and its full test
suite run with no embedding model and no Qdrant server, falling back to an
in-process vector index and reporting documents as `unavailable` until the extras
are installed.

This was a backend-plus-frontend stage delivered in two major features, each
merged via a CI-gated PR:

- **Major Feature 1 — document ingestion pipeline** (PR #21): `Document` +
  `DocumentChunk` models, the embeddings and vector-store integrations, the
  `DocumentService` ingestion pipeline (extract → chunk → embed → index),
  upload/list/delete REST, and a Knowledge Base UI.
- **Major Feature 2 — semantic search + grounding** (PR #22): `KnowledgeService`
  search, `GET /knowledge/search`, the `search_knowledge` retrieval tool that
  grounds answers with citations, a knowledge-search UI, and citation chips in
  chat.

> No agents, scheduled automation, or PostgreSQL/Redis/Docker were introduced
> (deferred to Stages 6 / 7 / 8).

---

## Objectives Completed

- **Document ingestion** — `DocumentService` owns extract → chunk → embed →
  index. Text extraction supports plain text, Markdown, and PDF (lazy `pypdf`);
  chunking is word-boundary-aware with overlap. Status lifecycle:
  `pending → indexing → indexed | unavailable | failed`.
- **Embeddings integration** — `EmbeddingModel` contract +
  `SentenceTransformerEmbedding` (lazy, process-cached; the torch stack loads
  only on first use).
- **Vector store integration** — `VectorStore` contract with two backends:
  `InProcessVectorStore` (zero-dependency brute-force cosine fallback, durable
  via re-seed) and `QdrantVectorStore` (lazy client, collection auto-created,
  falls back when unreachable).
- **Semantic search** — `KnowledgeService` embeds the query, searches the
  user-scoped index, and resolves hits to chunk text + source filename, ordered
  best-first. Re-seeds the in-process index from persisted chunk embeddings after
  a restart (no re-embedding).
- **Grounding tool** — `search_knowledge` read tool returns `[n]`-marked excerpts
  with filenames and instructs the model to cite; wired into the `ToolRegistry`
  via a new `knowledge` field on `ToolContext`.
- **REST** — `POST /documents/upload`, `GET /documents`, `GET /documents/{id}`,
  `GET /documents/status`, `DELETE /documents/{id}`, and
  `GET /knowledge/search`.
- **Frontend** — a Knowledge Base page (drag-and-drop upload, status badges,
  delete), a semantic-search box with ranked results, and citation chips that
  show grounded answers' sources in the Assistant.
- **Graceful degradation everywhere** — embeddings missing → documents stored as
  `unavailable` and re-indexable later; search returns no hits instead of
  raising; the UI surfaces an "offline" hint.

---

## Files Created

**Major Feature 1**

- `backend/models/document.py` (`Document`, `DocumentChunk`)
- `backend/repositories/document_repository.py`
- `backend/integrations/embeddings/{__init__,base,sentence_transformer}.py`
- `backend/integrations/vectorstore/{__init__,base,memory_store,qdrant_store}.py`
- `backend/services/{document_service,text_processing}.py`
- `backend/schemas/document.py`, `backend/api/routes/documents.py`
- `backend/requirements-knowledge.txt`, `backend/tests/test_stage5_documents.py`
- `frontend/src/features/documents/{api.ts,useDocuments.ts,format.ts}`
- `frontend/src/features/documents/components/{DocumentUpload,DocumentCard,DocumentList}.tsx`
- `frontend/src/pages/DocumentsPage.tsx`

**Major Feature 2**

- `backend/services/knowledge_service.py`, `backend/api/routes/knowledge.py`
- `backend/tests/test_stage5_knowledge.py`
- `frontend/src/features/documents/components/KnowledgeSearch.tsx`

**Docs**

- `docs/stage5/major-feature-1.md`, `docs/stage5/major-feature-2.md`
- `docs/stage-5-summary.md` — this file

## Files Modified

- `backend/config.py` — embeddings / vector-backend / Qdrant / chunking + upload
  settings
- `backend/services/factory.py` — embedding + vector-store + document + knowledge
  builders (KB integrations cached as process singletons); `search_knowledge`
  wired into the tool registry
- `backend/api/dependencies.py` — `get_document_service`, `get_knowledge_service`
- `backend/api/routes/__init__.py` — mount the documents + knowledge routers
- `backend/models/__init__.py` — register `Document` / `DocumentChunk`
- `backend/services/tools/base.py` — `knowledge` field on `ToolContext`
- `backend/services/tools/read_tools.py` — `SearchKnowledgeTool`
- `backend/services/ai_service.py` — system prompt mentions the KB + citing
- `frontend/src/api/client.ts` — `apiUpload` (multipart) + `apiDelete`
- `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx` — Knowledge
  route + nav entry
- `frontend/src/components/ai/ToolCallChip.tsx` — knowledge citation chip
- `CURRENT_SPRINT.md` — Stage 5 spec, then advanced to Stage 6

---

## Architectural Decisions

- **RAG reuses the tool-use loop; it adds nothing to it.** `search_knowledge` is
  a Stage-4-style read tool. Grounding introduces no write, agent, or
  confirmation logic — the chat/confirmation core is untouched.
- **Ingestion and search are separate services over a shared index.**
  `DocumentService` (write) and `KnowledgeService` (read) both talk to the
  embeddings + vector-store integrations through the integration seam, per the
  Service → Integration contract.
- **Heavy deps are opt-in and lazy.** sentence-transformers (torch), the Qdrant
  client, and pypdf live in `requirements-knowledge.txt`, are imported on first
  use, and degrade gracefully — the established voice/browser pattern.
- **Embeddings are persisted on chunk rows.** This makes the in-process fallback
  durable (re-seeded on demand after a restart, no re-embedding) and guarantees
  citations always have their source text regardless of the vector backend.
- **The vector store is swappable behind a contract.** Qdrant in production, an
  in-process cosine index for zero-setup development; selection is config-driven
  with automatic fallback when Qdrant is unreachable.
- **KB integrations are process singletons.** The embedding model and in-process
  store are built once in the factory, so search reads exactly the index that
  ingestion wrote.

---

## Verification

- `ruff check backend/` — passes
- `python -m pytest backend/tests/` — **116 passed** (16 documents + 8 knowledge
  + prior 92), all with deterministic fake embeddings (no model, torch, Qdrant,
  or network in tests)
- Frontend `tsc -b`, `vite build`, and `eslint` — all clean
- Smoke-tested the real factory wiring: graceful `unavailable` ingestion under
  default (no-embeddings) config; `search_knowledge` advertised in the registry
- CI (GitHub Actions) green on PRs #21 and #22

---

## Unresolved Issues / Technical Debt

- **Not verified against a real embedding model / Qdrant.** Implemented to spec
  and tested with fakes, but not run against installed sentence-transformers or a
  live Qdrant here; first real ingestion + search should be smoke-tested after
  `pip install -r backend/requirements-knowledge.txt`.
- **Re-index of `unavailable` documents is manual.** Documents ingested while
  embeddings were absent keep their chunks but no vectors; there is no re-index
  endpoint yet (re-upload, or add a `POST /documents/{id}/reindex`).
- **Synchronous ingestion.** Upload extracts + embeds inline in the request; fine
  for personal-scale files, but large PDFs would benefit from a background job
  (arrives naturally with Stage 7 scheduling).
- **In-process index is per-process.** The fallback re-seeds from the DB, but in a
  multi-worker deployment each worker holds its own copy; Qdrant is the answer at
  that scale.
- **Fixed chunking + top-k.** No re-ranking, hybrid keyword search, or
  per-document filters yet; straightforward future enhancements.
- **Single-user scoping.** Documents are owner-scoped like the rest of the app;
  per-user isolation waits on an auth stage.

---

## Recommendations for Stage 6 (Agents)

- Introduce `backend/agents/` with a base `Agent` interface and per-domain agents
  (Email, Calendar, Study, Notification) that **orchestrate services**, never
  calling integrations directly (ARCHITECTURE.md Agent → Service → Integration).
- Reuse the Stage 4 `ToolRegistry` / Stage 4.5 `ToolExecutor`: agents compose
  existing read/write tools into multi-step plans rather than introducing new
  side-effect paths. Per the roadmap, agents may run tool chains with reduced
  per-action confirmation — keep an **audit trail** for any destructive action.
- Ground agent reasoning with the Stage 5 `search_knowledge` retrieval where it
  helps (e.g. the Study Agent over uploaded course material).
- Add agent run visibility (steps, tools used, status) in the UI; keep it
  optional and read-only.
- Keep the modular-monolith boundaries: agents are a new layer above services,
  not a rewrite of the chat core.

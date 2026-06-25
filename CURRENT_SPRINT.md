# Current Sprint

Current Stage: Stage 5

Objective:

Give Personal OS a **knowledge system**: upload documents, embed and index them,
and let the assistant answer questions grounded in that personal knowledge base
(RAG). Retrieval is exposed as a tool inside the existing AI tool-use loop, so
grounded answers reuse the Stage 4 chat path and the Stage 4.5 confirmation flow
without changing the chat core.

This is a backend-plus-frontend stage. It builds on the Stage 4 `AIService` +
`ToolRegistry` and the ARCHITECTURE.md Service → Integration contract.

---

# Allowed Features

Backend:

- a `Document` model (DB) + a `DocumentService` owning ingestion: text
  extraction → chunking → embedding → indexing, and deletion
- an **embeddings integration** (sentence-transformers) — encodes text to
  vectors; lazily imported and degrading gracefully when absent
- a **vector store integration** (Qdrant client) for upserting + searching
  chunk vectors, with an in-process fallback so the app runs without a Qdrant
  server during development
- a `KnowledgeService` (or `RetrievalService`) exposing semantic search over the
  indexed chunks
- a `search_knowledge` **read tool** behind the existing `ToolRegistry` so the
  assistant can retrieve relevant chunks and ground its answers (with citations)
- REST: upload a document, list/delete documents, and a semantic-search endpoint

Frontend:

- a documents view: upload, list, and delete documents (with index status)
- citations surfaced in the assistant's grounded answers

---

# Architecture Contract

- **Integration layer** — the embeddings model and the Qdrant client are thin
  wrappers (encode / upsert / search); heavy deps load lazily so the app boots
  without them, mirroring the voice + browser pattern.
- **Service layer** — `DocumentService` owns ingestion and talks to the
  embeddings + vector integrations via the repository/integration seam;
  `KnowledgeService` owns search. Routes and tools stay thin.
- **RAG reuses the tool-use loop** — `search_knowledge` is a read tool like the
  Stage 4 read tools; grounding adds no new write, agent, or confirmation logic.
- **Graceful degradation** — when embeddings/Qdrant are unavailable, ingestion
  and the tool report unavailable instead of failing the app.

---

# Restrictions

DO NOT implement:

- agents / agent orchestration — Stage 6
- workflow automation / scheduled pipelines — Stage 7
- PostgreSQL / Redis / Docker — Stage 8
- new write tools or changes to the Stage 4.5 confirmation flow (retrieval is
  read-only)
- voice changes — Stage 4.7 is complete

Do not implement future stages beyond Stage 5.

---

# Deliverables

- `Document` model + `DocumentService` (ingestion: extract → chunk → embed →
  index) + `KnowledgeService` (semantic search)
- embeddings integration (sentence-transformers) + vector store integration
  (Qdrant, with an in-process fallback)
- a `search_knowledge` read tool grounding the assistant's answers, with
  citations
- document upload / list / delete + semantic-search REST endpoints
- a documents UI and citations surfaced in grounded answers

---

# Development Process

Build incrementally and pause for approval between major features:

Major Feature 1:
`Document` model + `DocumentService` ingestion pipeline (extract → chunk → embed
→ index) + the embeddings and vector-store integrations, plus document
upload/list/delete REST + a documents UI.

Major Feature 2:
`KnowledgeService` semantic search + the `search_knowledge` retrieval tool
grounding the assistant's answers (with citations surfaced in the chat UI).

After each major feature:

- explain decisions
- list files created / modified
- wait for approval

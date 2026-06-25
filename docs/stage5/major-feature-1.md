# Stage 5 — Major Feature 1: Document ingestion pipeline

**Status:** complete, pending approval before Major Feature 2.

Stage 5 gives Personal OS a **knowledge base**: upload documents, extract and
embed their text, and index the chunks for retrieval (RAG). Major Feature 1
delivers the ingestion half — the index that Major Feature 2's semantic search +
`search_knowledge` tool will read.

## What was built

### Backend

- **Models** (`backend/models/document.py`)
  - `Document` — uploaded file metadata + index status
    (`pending → indexing → indexed | unavailable | failed`).
  - `DocumentChunk` — an embedded text chunk; stores the chunk text and the
    embedding vector (JSON) so the in-process index survives a restart and chunk
    text is always available for citations.
- **Repository** (`backend/repositories/document_repository.py`) — document +
  chunk persistence and queries. No business logic.
- **Embeddings integration** (`backend/integrations/embeddings/`) — an
  `EmbeddingModel` contract with a lazy `SentenceTransformerEmbedding`
  implementation (process-cached; the heavy `sentence-transformers`/torch stack
  is imported only on first use, and `available()` reports False until then).
- **Vector store integration** (`backend/integrations/vectorstore/`) — a
  `VectorStore` contract with two backends:
  - `InProcessVectorStore` — zero-dependency brute-force cosine search (the
    development fallback), re-seedable from persisted chunk embeddings.
  - `QdrantVectorStore` — lazy `qdrant_client`; creates its collection on first
    use and falls back to in-process when Qdrant isn't installed/reachable.
- **Text processing** (`backend/services/text_processing.py`) — `extract_text`
  (plain text, Markdown, and lazy-`pypdf` PDF) and a word-boundary-aware
  overlapping `chunk_text`.
- **Service** (`backend/services/document_service.py`) — `DocumentService` owns
  the pipeline: extract → chunk → embed → index, plus list/get/delete. It talks
  to the integrations through the integration seam and degrades gracefully:
  missing embeddings → `unavailable` (chunks stored for later re-index); any
  extraction/encoding error → `failed` (recorded on the document, never raised
  to the caller).
- **REST** (`backend/api/routes/documents.py`, mounted under `/api/v1`):
  - `POST /documents/upload` — multipart upload → ingest.
  - `GET /documents` — list (newest first).
  - `GET /documents/{id}` — one document's status.
  - `GET /documents/status` — knowledge subsystem capabilities (for the UI).
  - `DELETE /documents/{id}` — delete a document and its chunks/vectors.
- **Wiring** — factory builders (`build_embedding_model`, `build_vector_store`,
  `build_document_service`), a `get_document_service` dependency, config
  (`embedding_model`, `vector_backend`, `qdrant_*`, `knowledge_chunk_*`,
  `knowledge_max_upload_bytes`), model registration, and an optional
  `backend/requirements-knowledge.txt`.

### Frontend

- `frontend/src/features/documents/` — typed API layer, React Query hooks
  (list/status/upload/delete, with brief polling while a file is indexing), and
  presentation components: `DocumentUpload` (drag-and-drop), `DocumentCard`,
  `DocumentList` (loading/error/empty states), plus a status-badge helper.
- `frontend/src/pages/DocumentsPage.tsx` — the **Knowledge Base** page, plus a
  router route (`/documents`) and a sidebar entry. Surfaces an "embeddings
  offline" hint when semantic search isn't installed.
- `frontend/src/api/client.ts` — added `apiUpload` (multipart) and `apiDelete`.

## Architecture notes

- The embeddings model and Qdrant client are **thin integrations** with lazy
  heavy deps, mirroring the voice + browser pattern. `DocumentService` (service
  layer) owns ingestion; routes stay thin.
- Embeddings + vectors are **persisted on chunk rows**, so the in-process
  fallback is durable across restarts (re-seeded on demand) and citations always
  have their source text regardless of the vector backend.
- Graceful degradation everywhere: the app boots and the test suite runs with no
  embedding model, no Qdrant, and no PDF library installed.

## Tests

`backend/tests/test_stage5_documents.py` (16 tests) — text extraction +
chunking, the in-process vector store (user scoping, deletion), the ingestion
pipeline (indexed / unavailable / failed paths), ownership-scoped delete,
in-memory re-seed, status, route registration, and an end-to-end
upload → list → delete REST flow via `TestClient` with a fake embedding. Full
backend suite: 108 passed. Frontend typechecks, lints, and builds clean.

## Deferred to Major Feature 2

- `KnowledgeService` semantic search + `GET /knowledge/search` endpoint.
- The `search_knowledge` read tool grounding the assistant's answers.
- Citations surfaced in the chat UI.

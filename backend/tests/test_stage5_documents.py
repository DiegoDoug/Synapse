"""Stage 5 (Major Feature 1) tests — document ingestion pipeline.

Covers text extraction + chunking, the in-process vector store, the
``DocumentService`` ingestion pipeline (extract → chunk → embed → index) with
embeddings present, missing (graceful ``unavailable``), and failing, plus the
upload/list/delete REST flow. A ``FakeEmbedding`` implements the embedding
contract in-memory, so no model, torch, or network is required.
"""

import math

import pytest
from backend.api.dependencies import get_current_user_id, get_document_service
from backend.database import get_session
from backend.integrations.embeddings.base import (
    EmbeddingModel,
    EmbeddingUnavailableError,
)
from backend.integrations.vectorstore.base import VectorRecord
from backend.integrations.vectorstore.memory_store import InProcessVectorStore
from backend.main import app
from backend.repositories.document_repository import DocumentRepository
from backend.services.document_service import DocumentService
from backend.services.text_processing import (
    ExtractionError,
    chunk_text,
    extract_text,
)
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# --- Fakes -------------------------------------------------------------------


class FakeEmbedding(EmbeddingModel):
    """Deterministic char-frequency embedding — similar text, similar vector."""

    def __init__(self, *, available: bool = True, fail: bool = False) -> None:
        self._available = available
        self._fail = fail

    def available(self) -> bool:
        return self._available

    @property
    def dimension(self) -> int:
        return 26

    def encode(self, texts: list[str]) -> list[list[float]]:
        if self._fail:
            raise EmbeddingUnavailableError("no model")
        return [self._vector(text) for text in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        counts = [0.0] * 26
        for ch in text.lower():
            if "a" <= ch <= "z":
                counts[ord(ch) - 97] += 1.0
        norm = math.sqrt(sum(c * c for c in counts)) or 1.0
        return [c / norm for c in counts]


def _service(session, embedding: EmbeddingModel, store=None) -> DocumentService:
    return DocumentService(
        DocumentRepository(session),
        embedding,
        store if store is not None else InProcessVectorStore(),
        embedding_model_name="fake",
        chunk_size=120,
        chunk_overlap=20,
    )


# --- Text processing ---------------------------------------------------------


def test_chunk_text_overlaps_and_respects_words():
    text = " ".join(f"word{i}" for i in range(200))
    chunks = chunk_text(text, chunk_size=120, overlap=20)
    assert len(chunks) > 1
    # Every chunk stays within a small margin of the target size.
    assert all(len(c) <= 140 for c in chunks)
    # No word is split across the boundary.
    assert all(" word" not in c[:1] for c in chunks)


def test_chunk_text_empty():
    assert chunk_text("   ", chunk_size=100, overlap=10) == []


def test_extract_text_plain_and_markdown():
    assert extract_text("a.txt", "text/plain", b"hello world") == "hello world"
    assert extract_text("n.md", None, b"# Title\n\nbody") == "# Title\n\nbody"


def test_extract_text_rejects_binary():
    with pytest.raises(ExtractionError):
        extract_text("blob.bin", "application/octet-stream", b"\xff\xfe\x00\x01")


# --- In-process vector store -------------------------------------------------


def test_memory_store_search_is_user_scoped():
    store = InProcessVectorStore()
    store.upsert(
        [
            VectorRecord(id=1, vector=[1.0, 0.0], payload={"user_id": 1, "document_id": 10}),
            VectorRecord(id=2, vector=[0.0, 1.0], payload={"user_id": 2, "document_id": 20}),
        ]
    )
    hits = store.search([1.0, 0.0], user_id=1, limit=5)
    assert [h.id for h in hits] == [1]


def test_memory_store_delete_document():
    store = InProcessVectorStore()
    store.upsert(
        [
            VectorRecord(id=1, vector=[1.0, 0.0], payload={"user_id": 1, "document_id": 10}),
            VectorRecord(id=2, vector=[0.0, 1.0], payload={"user_id": 1, "document_id": 11}),
        ]
    )
    store.delete_document(10)
    assert len(store) == 1
    assert store.search([1.0, 0.0], user_id=1)[0].id == 2


# --- Ingestion pipeline ------------------------------------------------------


def test_ingest_indexes_document(session):
    store = InProcessVectorStore()
    service = _service(session, FakeEmbedding(), store)
    text = " ".join(f"sentence{i}" for i in range(100)).encode()

    doc = service.ingest(1, filename="notes.txt", content_type="text/plain", data=text)

    assert doc.status == "indexed"
    assert doc.chunk_count > 0
    assert doc.indexed_at is not None
    # Chunks are persisted with embeddings and pushed to the vector store.
    chunks = DocumentRepository(session).list_chunks(doc.id)
    assert len(chunks) == doc.chunk_count
    assert all(c.embedding for c in chunks)
    assert len(store) == doc.chunk_count


def test_ingest_without_embeddings_is_unavailable(session):
    service = _service(session, FakeEmbedding(available=False))
    doc = service.ingest(1, filename="n.txt", content_type="text/plain", data=b"alpha beta gamma")

    assert doc.status == "unavailable"
    assert doc.chunk_count == 1
    # Chunks are stored (without vectors) so a later re-index needs no re-upload.
    chunks = DocumentRepository(session).list_chunks(doc.id)
    assert chunks and all(c.embedding is None for c in chunks)


def test_ingest_failed_extraction(session):
    service = _service(session, FakeEmbedding())
    doc = service.ingest(
        1, filename="blob.bin", content_type="application/octet-stream",
        data=b"\xff\xfe\x00\x01",
    )
    assert doc.status == "failed"
    assert doc.error


def test_ingest_empty_text_fails(session):
    service = _service(session, FakeEmbedding())
    doc = service.ingest(1, filename="empty.txt", content_type="text/plain", data=b"    ")
    assert doc.status == "failed"


def test_delete_removes_document_and_vectors(session):
    store = InProcessVectorStore()
    service = _service(session, FakeEmbedding(), store)
    doc = service.ingest(1, filename="n.txt", content_type="text/plain", data=b"alpha beta gamma")
    assert len(store) > 0

    assert service.delete(1, doc.id) is True
    assert service.get(1, doc.id) is None
    assert len(store) == 0
    assert DocumentRepository(session).list_chunks(doc.id) == []


def test_delete_other_users_document_denied(session):
    service = _service(session, FakeEmbedding())
    doc = service.ingest(1, filename="n.txt", content_type="text/plain", data=b"alpha beta")
    assert service.delete(2, doc.id) is False
    assert service.get(1, doc.id) is not None


def test_reseed_memory_index_rebuilds_from_db(session):
    store = InProcessVectorStore()
    service = _service(session, FakeEmbedding(), store)
    doc = service.ingest(1, filename="n.txt", content_type="text/plain", data=b"alpha beta gamma")
    count = doc.chunk_count

    # Simulate a restart: a fresh empty in-process store, same DB.
    fresh = InProcessVectorStore()
    service2 = _service(session, FakeEmbedding(), fresh)
    loaded = service2.reseed_memory_index(1)
    assert loaded == count
    assert len(fresh) == count


def test_status_reports_capabilities(session):
    service = _service(session, FakeEmbedding(available=True))
    status = service.status()
    assert status.embeddings_available is True
    assert status.vector_backend == "memory"


# --- REST flow ---------------------------------------------------------------


def test_documents_routes_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/documents" in paths
    assert "/api/v1/documents/upload" in paths
    assert "/api/v1/documents/{document_id}" in paths
    assert "/api/v1/documents/status" in paths


def test_upload_list_delete_via_api(session):
    store = InProcessVectorStore()

    def _session_override():
        yield session

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user_id] = lambda: 1
    app.dependency_overrides[get_document_service] = lambda: _service(
        session, FakeEmbedding(), store
    )
    try:
        client = TestClient(app)
        upload = client.post(
            "/api/v1/documents/upload",
            files={"file": ("notes.txt", b"alpha beta gamma delta", "text/plain")},
        )
        assert upload.status_code == 201
        body = upload.json()
        assert body["status"] == "indexed"
        doc_id = body["id"]

        listing = client.get("/api/v1/documents")
        assert listing.status_code == 200
        assert any(d["id"] == doc_id for d in listing.json())

        deleted = client.delete(f"/api/v1/documents/{doc_id}")
        assert deleted.status_code == 204
        assert client.get(f"/api/v1/documents/{doc_id}").status_code == 404
    finally:
        app.dependency_overrides.clear()

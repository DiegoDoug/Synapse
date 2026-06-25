"""Stage 5 (Major Feature 2) tests — semantic search + the search_knowledge tool.

Builds a small index with the in-memory ``DocumentService`` (Major Feature 1)
using a deterministic ``FakeEmbedding`` (char-frequency vectors, so lexically
similar text scores higher), then exercises ``KnowledgeService`` search, the
in-process re-seed after a simulated restart, the ``search_knowledge`` tool, and
the ``GET /knowledge/search`` endpoint. No model, torch, or network.
"""

import math

import pytest
from backend.api.dependencies import get_current_user_id, get_knowledge_service
from backend.database import get_session
from backend.integrations.embeddings.base import EmbeddingModel
from backend.integrations.vectorstore.memory_store import InProcessVectorStore
from backend.main import app
from backend.repositories.account_repository import AccountRepository
from backend.repositories.calendar_repository import CalendarRepository
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.email_repository import EmailRepository
from backend.repositories.notification_repository import NotificationRepository
from backend.services.document_service import DocumentService
from backend.services.knowledge_service import KnowledgeService
from backend.services.tools.base import ToolContext
from backend.services.tools.read_tools import SearchKnowledgeTool
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


class FakeEmbedding(EmbeddingModel):
    """Deterministic char-frequency embedding — similar text, similar vector."""

    def __init__(self, *, available: bool = True) -> None:
        self._available = available

    def available(self) -> bool:
        return self._available

    @property
    def dimension(self) -> int:
        return 26

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    @staticmethod
    def _vector(text: str) -> list[float]:
        counts = [0.0] * 26
        for ch in text.lower():
            if "a" <= ch <= "z":
                counts[ord(ch) - 97] += 1.0
        norm = math.sqrt(sum(c * c for c in counts)) or 1.0
        return [c / norm for c in counts]


def _doc_service(session, embedding, store) -> DocumentService:
    return DocumentService(
        DocumentRepository(session),
        embedding,
        store,
        embedding_model_name="fake",
        chunk_size=200,
        chunk_overlap=20,
    )


def _knowledge(session, embedding, store) -> KnowledgeService:
    return KnowledgeService(DocumentRepository(session), embedding, store)


def _seed_two_docs(session, embedding, store) -> None:
    docs = _doc_service(session, embedding, store)
    docs.ingest(
        1,
        filename="hurdles.md",
        content_type="text/markdown",
        data=b"hurdles training sprint technique blocks acceleration",
    )
    docs.ingest(
        1,
        filename="vacation.md",
        content_type="text/markdown",
        data=b"vacation beach travel itinerary flights hotel booking",
    )


# --- KnowledgeService search -------------------------------------------------


def test_search_returns_relevant_document_first(session):
    store = InProcessVectorStore()
    embedding = FakeEmbedding()
    _seed_two_docs(session, embedding, store)

    hits = _knowledge(session, embedding, store).search(1, "hurdles training sprint")
    assert hits
    assert hits[0].filename == "hurdles.md"
    assert hits[0].content
    assert hits[0].score >= hits[-1].score  # ordered best-first


def test_search_unavailable_returns_empty(session):
    store = InProcessVectorStore()
    _seed_two_docs(session, FakeEmbedding(), store)
    # A service whose embeddings are "uninstalled" yields no hits, never raises.
    offline = _knowledge(session, FakeEmbedding(available=False), store)
    assert offline.search(1, "hurdles") == []
    assert offline.available() is False


def test_search_is_user_scoped(session):
    store = InProcessVectorStore()
    embedding = FakeEmbedding()
    _seed_two_docs(session, embedding, store)
    # User 2 has no documents, so search returns nothing.
    assert _knowledge(session, embedding, store).search(2, "hurdles") == []


def test_search_reseeds_index_after_restart(session):
    embedding = FakeEmbedding()
    _seed_two_docs(session, embedding, InProcessVectorStore())

    # Simulate a process restart: a fresh, empty in-process store, same DB. The
    # index is rebuilt from the embeddings persisted on the chunk rows.
    fresh = InProcessVectorStore()
    knowledge = _knowledge(session, embedding, fresh)
    assert len(fresh) == 0
    hits = knowledge.search(1, "vacation beach travel")
    assert hits and hits[0].filename == "vacation.md"
    assert len(fresh) > 0  # the store was re-seeded on demand


# --- search_knowledge tool ---------------------------------------------------


def _context(session, knowledge) -> ToolContext:
    return ToolContext(
        user_id=1,
        accounts=AccountRepository(session),
        emails=EmailRepository(session),
        events=CalendarRepository(session),
        notifications=NotificationRepository(session),
        knowledge=knowledge,
    )


def test_search_knowledge_tool_formats_citations(session):
    store = InProcessVectorStore()
    embedding = FakeEmbedding()
    _seed_two_docs(session, embedding, store)
    context = _context(session, _knowledge(session, embedding, store))

    result = SearchKnowledgeTool().run({"query": "hurdles training"}, context)
    assert "[1]" in result
    assert "hurdles.md" in result


def test_search_knowledge_tool_unavailable_without_knowledge(session):
    context = _context(session, None)
    result = SearchKnowledgeTool().run({"query": "anything"}, context)
    assert "unavailable" in result.lower()


def test_search_knowledge_tool_no_results(session):
    store = InProcessVectorStore()
    embedding = FakeEmbedding()
    context = _context(session, _knowledge(session, embedding, store))
    result = SearchKnowledgeTool().run({"query": "nothing indexed yet"}, context)
    assert "No relevant passages" in result


# --- REST --------------------------------------------------------------------


def test_knowledge_route_registered():
    assert "/api/v1/knowledge/search" in set(app.openapi()["paths"])


def test_search_endpoint(session):
    store = InProcessVectorStore()
    embedding = FakeEmbedding()
    _seed_two_docs(session, embedding, store)

    def _session_override():
        yield session

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[get_current_user_id] = lambda: 1
    app.dependency_overrides[get_knowledge_service] = lambda: _knowledge(
        session, embedding, store
    )
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/knowledge/search", params={"query": "beach travel"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["available"] is True
        assert body["hits"]
        assert body["hits"][0]["filename"] == "vacation.md"
    finally:
        app.dependency_overrides.clear()

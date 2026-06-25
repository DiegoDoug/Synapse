"""Document + DocumentChunk data access. No business logic."""

from datetime import UTC, datetime

from sqlmodel import Session, select

from backend.models.document import Document, DocumentChunk


class DocumentRepository:
    """Queries and transactions for knowledge-base documents and their chunks."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Documents --------------------------------------------------------

    def get(self, document_id: int) -> Document | None:
        return self._session.get(Document, document_id)

    def get_for_user(self, user_id: int, document_id: int) -> Document | None:
        document = self._session.get(Document, document_id)
        if document is None or document.user_id != user_id:
            return None
        return document

    def list_for_user(self, user_id: int, *, limit: int = 100) -> list[Document]:
        statement = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())  # type: ignore[union-attr]
            .limit(limit)
        )
        return list(self._session.exec(statement).all())

    def add(self, document: Document) -> Document:
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def update(self, document: Document) -> Document:
        document.updated_at = datetime.now(UTC)
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def delete(self, document: Document) -> None:
        self.delete_chunks(document.id)
        self._session.delete(document)
        self._session.commit()

    # --- Chunks -----------------------------------------------------------

    def add_chunks(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        for chunk in chunks:
            self._session.add(chunk)
        self._session.commit()
        for chunk in chunks:
            self._session.refresh(chunk)
        return chunks

    def list_chunks(self, document_id: int) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())  # type: ignore[union-attr]
        )
        return list(self._session.exec(statement).all())

    def list_embedded_chunks(self, user_id: int) -> list[DocumentChunk]:
        """All of a user's chunks that carry a stored embedding (for re-indexing
        the in-process vector store)."""
        statement = select(DocumentChunk).where(
            DocumentChunk.user_id == user_id,
            DocumentChunk.embedding.is_not(None),  # type: ignore[union-attr]
        )
        return list(self._session.exec(statement).all())

    def get_chunks(self, chunk_ids: list[int]) -> list[DocumentChunk]:
        if not chunk_ids:
            return []
        statement = select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))  # type: ignore[union-attr]
        return list(self._session.exec(statement).all())

    def delete_chunks(self, document_id: int) -> None:
        for chunk in self.list_chunks(document_id):
            self._session.delete(chunk)
        self._session.commit()

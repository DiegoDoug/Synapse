"""Document routes — the personal knowledge base (RAG ingestion + management).

Endpoints (under /api/v1):
- GET    /documents              list the user's documents (newest first)
- GET    /documents/status       knowledge subsystem capabilities (for the UI)
- GET    /documents/{id}         fetch one document's metadata + index status
- POST   /documents/upload       upload a file → extract, chunk, embed, index
- DELETE /documents/{id}         delete a document and its chunks/vectors

All endpoints are scoped to the current (single) user. Semantic search and the
``search_knowledge`` retrieval tool are added in Major Feature 2; ingestion here
produces the index they read.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.api.dependencies import get_current_user_id, get_document_service
from backend.config import Settings, get_settings
from backend.schemas.document import DocumentRead, KnowledgeStatus
from backend.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentRead])
def list_documents(
    user_id: int = Depends(get_current_user_id),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentRead]:
    return service.list(user_id)


@router.get("/status", response_model=KnowledgeStatus)
def knowledge_status(
    service: DocumentService = Depends(get_document_service),
) -> KnowledgeStatus:
    return service.status()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    document = service.get(user_id, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentRead, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
    settings: Settings = Depends(get_settings),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > settings.knowledge_max_upload_bytes:
        raise HTTPException(status_code=413, detail="The file is too large.")
    return service.ingest(
        user_id,
        filename=file.filename or "untitled",
        content_type=file.content_type,
        data=data,
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    user_id: int = Depends(get_current_user_id),
    service: DocumentService = Depends(get_document_service),
) -> None:
    if not service.delete(user_id, document_id):
        raise HTTPException(status_code=404, detail="Document not found")

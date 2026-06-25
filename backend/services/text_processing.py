"""Text extraction + chunking helpers for document ingestion.

Pure functions with no I/O beyond decoding the uploaded bytes. PDF parsing uses
``pypdf`` imported lazily so the base install stays light; an unsupported or
unreadable file raises ``ExtractionError`` for the service to record as a failed
document rather than crashing the request.
"""

from __future__ import annotations

import io

_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".text", ".rst", ".csv", ".log"}
_TEXT_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


class ExtractionError(ValueError):
    """Raised when text cannot be extracted from an uploaded file."""


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot != -1 else ""


def extract_text(filename: str, content_type: str | None, data: bytes) -> str:
    """Extract UTF-8 text from an uploaded file based on its type/extension."""
    extension = _extension(filename)
    ctype = (content_type or "").split(";")[0].strip().lower()

    if extension == ".pdf" or ctype == "application/pdf":
        return _extract_pdf(data)

    if (
        extension in _TEXT_EXTENSIONS
        or ctype in _TEXT_CONTENT_TYPES
        or ctype.startswith("text/")
    ):
        return data.decode("utf-8", errors="replace")

    # Unknown type: try a best-effort UTF-8 decode; reject if it looks binary.
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionError(
            f"Unsupported file type for '{filename}'. Upload text, Markdown, or PDF."
        ) from exc
    return text


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:  # noqa: BLE001 — pypdf not installed
        raise ExtractionError(
            "PDF support is not installed (add pypdf via "
            "backend/requirements-knowledge.txt)."
        ) from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:  # noqa: BLE001 — malformed PDF
        raise ExtractionError(f"Could not read PDF: {exc}") from exc
    return "\n\n".join(pages)


def chunk_text(
    text: str, *, chunk_size: int = 1000, overlap: int = 150
) -> list[str]:
    """Split text into overlapping chunks that respect word boundaries.

    Chunks are ~``chunk_size`` characters with ``overlap`` characters of trailing
    context carried into the next chunk, so a sentence split across a boundary
    still appears whole in at least one chunk.
    """
    words = text.split()
    if not words:
        return []
    if overlap >= chunk_size:
        overlap = chunk_size // 4

    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        # +1 accounts for the joining space.
        if length + len(word) + 1 > chunk_size and current:
            chunks.append(" ".join(current))
            current, length = _carry_overlap(current, overlap)
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def _carry_overlap(words: list[str], overlap: int) -> tuple[list[str], int]:
    """Return the trailing words (and their char length) to seed the next chunk."""
    carried: list[str] = []
    length = 0
    for word in reversed(words):
        if length + len(word) + 1 > overlap:
            break
        carried.insert(0, word)
        length += len(word) + 1
    return carried, length

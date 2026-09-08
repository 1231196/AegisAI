"""Pydantic schemas for the document endpoints (Epic 3 / US-008..US-014)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# Extensions accepted by US-008's acceptance criteria. Keyed by the
# lower-cased suffix (without the dot) so the router can validate with
# a single dict lookup; the value is the ``file_type`` label stored on
# the row and forwarded to backend-ai so it knows which parser to run.
ALLOWED_EXTENSIONS: dict[str, str] = {
    "pdf": "pdf",
    "docx": "docx",
    "txt": "txt",
    "md": "md",
    "markdown": "md",
    "csv": "csv",
}

DOCUMENT_STATUSES = frozenset({"processing", "indexed", "failed"})


class DocumentOut(BaseModel):
    """Outbound representation of a document row."""

    id: str
    organization_id: str
    uploaded_by: str
    filename: str
    file_type: str
    size_bytes: int
    status: str
    chunk_count: int | None = None
    content_hash: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    indexed_at: datetime | None = None


class DocumentStatusUpdateRequest(BaseModel):
    """Body of the internal callback PATCH backend-ai sends once a
    document finishes (or fails) indexing.

    Not part of the public API surface — gated by ``X-Internal-Token``,
    not a user JWT. See ``app.documents.internal_auth``.
    """

    status: str = Field(description="'indexed' or 'failed'")
    chunk_count: int | None = None
    content_hash: str | None = None
    error_message: str | None = None

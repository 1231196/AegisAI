"""Request schemas for the internal indexing API."""

from __future__ import annotations

from pydantic import BaseModel


class IndexRequest(BaseModel):
    """Body of POST /index — sent only by backend-api."""

    document_id: str
    organization_id: str
    storage_path: str
    filename: str
    file_type: str
    previous_hash: str | None = None

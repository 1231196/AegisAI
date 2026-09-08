"""Request/response schemas for the internal search API (Epic 4)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Body of POST /search — sent only by backend-api."""

    query: str = Field(min_length=1, max_length=1000)
    organization_id: str
    top_k: int | None = None
    final_k: int | None = Field(default=None, ge=5, le=20)


class SourceResult(BaseModel):
    """One retrieved chunk with full source attribution (US-019)."""

    document_id: str
    filename: str
    page_number: int | None
    chunk_index: int
    text: str
    excerpt: str
    score: float
    rerank_score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SourceResult]
    retrieved_count: int
    reranked_count: int

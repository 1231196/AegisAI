"""Pydantic schemas for the search endpoint (Epic 4 / US-015..US-019)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Body of POST /search. ``organization_id`` is deliberately not a
    field here — it's derived from the caller's own account, never
    accepted from the client, so a search can't be pointed at another
    tenant's knowledge base."""

    query: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=200)
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

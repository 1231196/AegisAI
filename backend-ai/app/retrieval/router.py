"""HTTP surface for search (US-015..US-019).

Internal-only — backend-api is the sole caller, gated by the same
shared-secret dependency already defined for the indexing endpoints
(reused here rather than duplicated).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.indexing.router import require_internal_token
from app.retrieval.schemas import SearchRequest, SearchResponse
from app.retrieval.service import run_search

router = APIRouter(tags=["retrieval"])


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_internal_token)],
)
def search(payload: SearchRequest) -> SearchResponse:
    return run_search(payload)

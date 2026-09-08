"""Search router (Epic 4 / US-015..US-019).

Gated by ``search_knowledge_base`` — the same permission GET
/documents already uses (the broadest "can see the KB" permission
every staff role holds). Always scoped to the caller's own
organisation; no cross-tenant search in this pass — not asked for,
and a platform_admin searching every tenant's content at once isn't
obviously useful without a target org to pick.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_permission
from app.documents.ai_client import SearchServiceError, run_search
from app.search.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    current_user: dict = Depends(require_permission("search_knowledge_base")),
) -> SearchResponse:
    try:
        result = run_search(
            query=payload.query,
            organization_id=current_user["organization_id"],
            top_k=payload.top_k,
            final_k=payload.final_k,
        )
    except SearchServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach the search service: {exc}",
        ) from exc
    return SearchResponse(**result)

"""HTTP surface for the indexing pipeline.

Internal-only — backend-api is the sole caller. Gated by the same
shared-secret pattern as backend-api's callback endpoint
(``app.documents.internal_auth`` on that side); there is no user JWT
involved on either side of this hop.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status

from app.config import settings
from app.indexing import service, vector_store
from app.indexing.schemas import IndexRequest

logger = logging.getLogger(__name__)

router = APIRouter(tags=["indexing"])


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    if x_internal_token is None or not hmac.compare_digest(
        x_internal_token, settings.internal_service_token
    ):
        logger.warning("indexing-request auth failure: missing or invalid X-Internal-Token")
        raise HTTPException(status_code=401, detail="Invalid internal service token")


@router.post(
    "/index",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_internal_token)],
)
def request_indexing(payload: IndexRequest, background_tasks: BackgroundTasks) -> dict:
    """Accept an indexing job and return immediately.

    The actual parse/chunk/embed/store pipeline runs in its own
    background task — this response only confirms the job was
    scheduled, not that it finished. backend-api learns the terminal
    state via the callback in ``service._report_status``.
    """
    background_tasks.add_task(
        service.index_document,
        document_id=payload.document_id,
        organization_id=payload.organization_id,
        storage_path=payload.storage_path,
        filename=payload.filename,
        file_type=payload.file_type,
        previous_hash=payload.previous_hash,
    )
    return {"accepted": True}


@router.post(
    "/index/{document_id}/delete",
    dependencies=[Depends(require_internal_token)],
)
def request_deletion(document_id: str) -> dict:
    """Drop every Qdrant point for ``document_id``. Idempotent — deleting
    a document with no points is not an error."""
    vector_store.delete_document(document_id)
    return {"deleted": True}

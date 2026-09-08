"""Document router (Epic 3 / US-008..US-014).

Permission model (mirrors the catalog in ``app.auth.permissions``):

* ``upload_documents``      — POST /documents (US-008)
* ``search_knowledge_base``  — GET /documents, GET /documents/{id} (broadest
  "can see the KB" permission every staff role holds)
* ``delete_org_documents``  — DELETE any document in the caller's org
* ``delete_own_documents``  — DELETE only documents the caller uploaded
  themselves (support_engineer has this but not ``delete_org_documents``)
* ``reindex_documents``     — POST /documents/{id}/reindex (US-014)

Tenant scoping follows the same ``is_cross_tenant`` pattern already
used in ``app.orgs.router`` / ``app.users.router``: ``platform_admin``
sees every organisation's documents, everyone else only their own.

``PATCH /internal/documents/{id}/status`` is not part of the
user-facing surface — see ``internal_auth.require_internal_token``.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.auth.dependencies import require_permission
from app.auth.permissions import has_permission
from app.auth.schemas import is_cross_tenant
from app.config import settings
from app.documents.ai_client import trigger_deletion, trigger_indexing
from app.documents.internal_auth import require_internal_token
from app.documents.repositories import DocumentRepository
from app.documents.schemas import (
    ALLOWED_EXTENSIONS,
    DocumentOut,
    DocumentStatusUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
internal_router = APIRouter(prefix="/internal/documents", tags=["internal"])


def _to_document_out(record: dict) -> DocumentOut:
    return DocumentOut(**record)


def _extension_of(filename: str) -> str:
    return Path(filename).suffix.lstrip(".").lower()


def _document_or_404(document_id: str, current_user: dict) -> dict:
    record = DocumentRepository.get_by_id(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not is_cross_tenant(current_user.get("role")):
        if record["organization_id"] != current_user["organization_id"]:
            # Foreign-org document: 404, not 403, so existence isn't leaked.
            raise HTTPException(status_code=404, detail="Document not found")
    return record


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: dict = Depends(require_permission("upload_documents")),
) -> DocumentOut:
    """Upload a document (US-008).

    Validates extension + size, writes the file to the shared
    ``documents-data`` volume, creates the metadata row with
    ``status=processing``, and schedules the indexing call to
    backend-ai as a background task so the response returns
    immediately — the client polls ``GET /documents/{id}`` for the
    terminal ``indexed``/``failed`` state.
    """
    filename = file.filename or ""
    extension = _extension_of(filename)
    file_type = ALLOWED_EXTENSIONS.get(extension)
    if file_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '.{extension}'. Allowed: "
                f"{', '.join(sorted(set(ALLOWED_EXTENSIONS.values())))}"
            ),
        )

    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(contents) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"File exceeds the "
                f"{settings.max_upload_size_bytes // (1024 * 1024)}MB limit"
            ),
        )

    record = DocumentRepository.create(
        organization_id=current_user["organization_id"],
        uploaded_by=current_user["id"],
        filename=filename,
        file_type=file_type,
        size_bytes=len(contents),
        # Placeholder path; replaced below once we know the document id
        # (the directory is keyed by id to keep re-uploads of the same
        # filename collision-free).
        storage_path="",
        status="processing",
    )

    doc_dir = Path(settings.documents_storage_path) / current_user["organization_id"] / record["id"]
    doc_dir.mkdir(parents=True, exist_ok=True)
    storage_path = doc_dir / filename
    storage_path.write_bytes(contents)

    record = DocumentRepository.update(record["id"], storage_path=str(storage_path))
    assert record is not None

    background_tasks.add_task(
        trigger_indexing,
        document_id=record["id"],
        organization_id=record["organization_id"],
        storage_path=record["storage_path"],
        filename=record["filename"],
        file_type=record["file_type"],
        previous_hash=None,
    )
    return _to_document_out(record)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: dict = Depends(require_permission("search_knowledge_base")),
) -> list[DocumentOut]:
    if is_cross_tenant(current_user.get("role")):
        records = DocumentRepository.list_all()
    else:
        records = DocumentRepository.list_in_organization(current_user["organization_id"])
    return [_to_document_out(r) for r in records]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    current_user: dict = Depends(require_permission("search_knowledge_base")),
) -> DocumentOut:
    record = _document_or_404(document_id, current_user)
    return _to_document_out(record)


@router.post("/{document_id}/reindex", response_model=DocumentOut)
def reindex_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_permission("reindex_documents")),
) -> DocumentOut:
    """Force a reindex (US-014). Incremental by content hash (US-013):
    backend-ai compares against ``previous_hash`` and skips
    re-embedding entirely when the file is unchanged.
    """
    record = _document_or_404(document_id, current_user)
    record = DocumentRepository.update(document_id, status="processing")
    assert record is not None

    background_tasks.add_task(
        trigger_indexing,
        document_id=record["id"],
        organization_id=record["organization_id"],
        storage_path=record["storage_path"],
        filename=record["filename"],
        file_type=record["file_type"],
        previous_hash=record["content_hash"],
    )
    return _to_document_out(record)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: dict = Depends(require_permission("delete_own_documents")),
) -> None:
    """Delete a document (US-014).

    Callers with ``delete_org_documents`` (admin/platform_admin) may
    delete any document in-scope; callers with only
    ``delete_own_documents`` (support_engineer) may delete only
    documents they uploaded themselves.
    """
    record = _document_or_404(document_id, current_user)

    role = current_user.get("role")
    can_delete_any = has_permission(role or "", "delete_org_documents")
    if not can_delete_any and record["uploaded_by"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You may only delete documents you uploaded",
        )

    if not trigger_deletion(document_id):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the indexing service; nothing was deleted. Try again.",
        )

    storage_path = Path(record["storage_path"])
    try:
        if storage_path.exists():
            storage_path.unlink()
            # Best-effort cleanup of the now-empty per-document directory.
            storage_path.parent.rmdir()
    except OSError:
        logger.warning("failed to remove stored file for document %s", document_id, exc_info=True)

    DocumentRepository.delete(document_id)
    return None


@internal_router.patch(
    "/{document_id}/status",
    response_model=DocumentOut,
    dependencies=[Depends(require_internal_token)],
)
def update_document_status(
    document_id: str,
    payload: DocumentStatusUpdateRequest,
) -> DocumentOut:
    """Callback backend-ai uses to report indexing completion/failure.

    Gated by the shared-secret ``X-Internal-Token`` header, not a user
    JWT — see ``app.documents.internal_auth``.
    """
    record = DocumentRepository.get_by_id(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found")

    if payload.status == "indexed":
        # US-013: the "unchanged, skipped re-embedding" callback omits
        # chunk_count entirely (backend-ai never recomputed it) — fall
        # back to the existing row's value rather than treating the
        # omission as "zero chunks", which would silently wipe a valid
        # count on every no-op reindex.
        chunk_count = (
            payload.chunk_count
            if payload.chunk_count is not None
            else (record["chunk_count"] or 0)
        )
        updated = DocumentRepository.mark_indexed(
            document_id,
            chunk_count=chunk_count,
            content_hash=payload.content_hash or record["content_hash"] or "",
        )
    elif payload.status == "failed":
        updated = DocumentRepository.mark_failed(
            document_id,
            error_message=payload.error_message or "Indexing failed",
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown status '{payload.status}'",
        )
    assert updated is not None
    return _to_document_out(updated)

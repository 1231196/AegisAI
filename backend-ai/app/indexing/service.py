"""Indexing orchestrator (US-008..US-013): parse -> chunk -> embed -> store.

Runs inside backend-ai's own ``BackgroundTasks`` job (scheduled by
``router.request_indexing``), so it's free to take as long as it needs
— nothing is waiting synchronously on the return value. The only
observable side effect is the callback to backend-api's internal
status endpoint once the job finishes (success or failure).

Indexing jobs are serialized process-wide via the shared
``app.model_lock.MODEL_LOCK`` — see that module for why this lock is
global across indexing/retrieval/chat rather than scoped to just this
file.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import httpx

from app.config import settings
from app.indexing import chunking, embeddings, parsers, vector_store
from app.model_lock import MODEL_LOCK

logger = logging.getLogger(__name__)

_CALLBACK_TIMEOUT = httpx.Timeout(10.0)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _report_status(
    document_id: str,
    *,
    status: str,
    chunk_count: int | None = None,
    content_hash: str | None = None,
    error_message: str | None = None,
) -> None:
    try:
        response = httpx.patch(
            f"{settings.backend_api_url}/internal/documents/{document_id}/status",
            json={
                "status": status,
                "chunk_count": chunk_count,
                "content_hash": content_hash,
                "error_message": error_message,
            },
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=_CALLBACK_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # Nothing left to do here — this *is* the error-reporting path.
        # If backend-api is unreachable, the document is stuck at
        # 'processing' until an operator investigates; no retry queue
        # in this pass.
        logger.exception(
            "failed to report status '%s' for document %s to backend-api",
            status,
            document_id,
        )


def index_document(
    *,
    document_id: str,
    organization_id: str,
    storage_path: str,
    filename: str,
    file_type: str,
    previous_hash: str | None,
) -> None:
    path = Path(storage_path)
    with MODEL_LOCK:
        _run_indexing(
            document_id=document_id,
            organization_id=organization_id,
            path=path,
            filename=filename,
            file_type=file_type,
            previous_hash=previous_hash,
        )


def _run_indexing(
    *,
    document_id: str,
    organization_id: str,
    path: Path,
    filename: str,
    file_type: str,
    previous_hash: str | None,
) -> None:
    try:
        content_hash = _hash_file(path)

        if previous_hash is not None and previous_hash == content_hash:
            # US-013: file unchanged since the last successful index —
            # skip the expensive parse/chunk/embed pass entirely.
            logger.info(
                "document %s unchanged (hash match); skipping re-embed", document_id
            )
            _report_status(document_id, status="indexed", content_hash=content_hash)
            return

        pages = parsers.extract_pages(path, file_type)
        page_chunks = chunking.chunk_pages(pages, file_type)
        if not page_chunks:
            _report_status(
                document_id,
                status="failed",
                error_message="No extractable text found in document",
            )
            return

        page_numbers = [page_number for page_number, _ in page_chunks]
        chunks = [chunk for _, chunk in page_chunks]
        vectors = embeddings.embed_texts(chunks)

        # Drop any prior points before upserting the new set so a
        # reindex that produces fewer chunks than before doesn't leave
        # stale orphaned points behind.
        vector_store.delete_document(document_id)
        vector_store.upsert_chunks(
            document_id=document_id,
            organization_id=organization_id,
            filename=filename,
            chunks=chunks,
            vectors=vectors,
            page_numbers=page_numbers,
        )

        _report_status(
            document_id,
            status="indexed",
            chunk_count=len(chunks),
            content_hash=content_hash,
        )
    except Exception as exc:
        logger.exception("indexing failed for document %s", document_id)
        _report_status(document_id, status="failed", error_message=str(exc))

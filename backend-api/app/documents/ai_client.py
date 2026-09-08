"""Thin HTTP client for backend-api -> backend-ai calls (Epic 3, 4, 5).

The indexing calls below are cheap "accept the job" round-trips, not
the indexing work itself: backend-ai's ``/index`` handler schedules
its own background task and returns 202 immediately, then reports the
real result later via the internal callback endpoint
(``PATCH /internal/documents/{id}/status``, see ``internal_auth.py``).
That's why a short timeout is safe there even though the underlying
parse/chunk/embed pipeline can take much longer.

``run_search`` (Epic 4) and ``stream_chat`` (Epic 5) are different:
both are called synchronously from within a request handler, so
failures are raised — not swallowed — for the router to translate
into the right HTTP response, and the timeouts are longer since the
caller is genuinely waiting on the full pipeline (retrieval, or
retrieval + LLM streaming) to run.
"""

from __future__ import annotations

import logging
from typing import Iterator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0)
# Reranking up to retrieval_initial_k (100) candidates is the slow
# step of a search request; 30s is generous headroom above the
# few-second steady-state latency observed in testing.
_SEARCH_TIMEOUT = httpx.Timeout(30.0)
# Chat streams retrieval (same cost as search) *plus* the LLM's full
# generation — the connect/write legs should still fail fast, but the
# read leg needs to stay open for as long as tokens keep arriving.
_CHAT_TIMEOUT = httpx.Timeout(10.0, read=120.0)


class SearchServiceError(Exception):
    """Raised when backend-ai's search endpoint is unreachable or errors."""


def trigger_indexing(
    *,
    document_id: str,
    organization_id: str,
    storage_path: str,
    filename: str,
    file_type: str,
    previous_hash: str | None,
) -> None:
    """Ask backend-ai to (re)index a document.

    Called from a FastAPI ``BackgroundTasks`` job, so there's no
    request context to propagate an error to — a failure to even
    *reach* backend-ai is handled here by marking the document
    'failed' directly, since nothing downstream would otherwise
    surface it.
    """
    try:
        response = httpx.post(
            f"{settings.ai_backend_url}/index",
            json={
                "document_id": document_id,
                "organization_id": organization_id,
                "storage_path": storage_path,
                "filename": filename,
                "file_type": file_type,
                "previous_hash": previous_hash,
            },
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning(
            "failed to trigger indexing for document %s: %r", document_id, exc
        )
        # Local import avoids a module-level circular import
        # (repositories.py has no reason to know about this client).
        from app.documents.repositories import DocumentRepository

        DocumentRepository.mark_failed(
            document_id,
            error_message=f"Could not reach indexing service: {exc}",
        )


def trigger_deletion(document_id: str) -> bool:
    """Ask backend-ai to drop this document's Qdrant points.

    Returns True on success — including "nothing to delete" (backend-ai
    404s when it has no points for this id), which keeps
    DELETE /documents/{id} idempotent. Returns False on any other
    failure; the router turns that into a 502 and deletes nothing,
    since an orphaned Postgres row is recoverable (retry the delete)
    but orphaned Qdrant vectors with no owning row are not.
    """
    try:
        response = httpx.post(
            f"{settings.ai_backend_url}/index/{document_id}/delete",
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=_TIMEOUT,
        )
        if response.status_code == 404:
            return True
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("failed to delete index for document %s: %r", document_id, exc)
        return False


def run_search(
    *,
    query: str,
    organization_id: str,
    top_k: int | None,
    final_k: int | None,
) -> dict:
    """Run a knowledge-base search via backend-ai's retrieval pipeline
    (Epic 4). Raises ``SearchServiceError`` on any failure — the
    router turns that into a 502, since there's no partial result
    worth returning.
    """
    try:
        response = httpx.post(
            f"{settings.ai_backend_url}/search",
            json={
                "query": query,
                "organization_id": organization_id,
                "top_k": top_k,
                "final_k": final_k,
            },
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=_SEARCH_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        logger.warning("search request failed: %r", exc)
        raise SearchServiceError(str(exc)) from exc


def stream_chat(
    *,
    query: str,
    organization_id: str,
    history: list[dict],
) -> Iterator[tuple[str, str]]:
    """Stream a RAG chat response from backend-ai's ``/chat`` endpoint
    (Epic 5). Yields ``(event, data)`` pairs parsed from the upstream
    SSE stream — ``event`` is one of "sources"/"token"/"done", ``data``
    is that event's raw JSON string.

    Parses the SSE framing properly (line-by-line, tracking the
    current ``event:`` until the next blank line) rather than
    forwarding raw bytes — HTTP chunk boundaries don't reliably line
    up with SSE message boundaries, so a byte-passthrough proxy could
    split an event across two chunks. The router re-serialises each
    yielded pair back into SSE for its own response, which also
    guarantees well-formed output regardless of how backend-ai chunked
    it.

    Raises ``SearchServiceError`` if the connection fails at any point
    (before or mid-stream) — the router's ``finally`` still persists
    whatever was captured up to that point.
    """
    try:
        with httpx.stream(
            "POST",
            f"{settings.ai_backend_url}/chat",
            json={
                "query": query,
                "organization_id": organization_id,
                "history": history,
            },
            headers={"X-Internal-Token": settings.internal_service_token},
            timeout=_CHAT_TIMEOUT,
        ) as response:
            response.raise_for_status()
            event_type: str | None = None
            for line in response.iter_lines():
                if line == "":
                    event_type = None
                    continue
                if line.startswith("event:"):
                    event_type = line[len("event:") :].strip()
                elif line.startswith("data:") and event_type is not None:
                    yield event_type, line[len("data:") :].strip()
    except httpx.HTTPError as exc:
        logger.warning("chat stream failed: %r", exc)
        raise SearchServiceError(str(exc)) from exc

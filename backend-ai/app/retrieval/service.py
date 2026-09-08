"""Search orchestrator (US-015..US-019): the full retrieval pipeline.

embed query -> hybrid retrieve (top_k) -> cross-encoder rerank ->
context selection (dedup, final_k) -> source-attributed results.

Unlike indexing, this runs synchronously in the request/response cycle
— search is a read the caller is waiting on, not a background job.

The embed/rerank steps run under the shared ``app.model_lock.MODEL_LOCK``
— see that module: concurrent calls into the native embedding/reranker
models from separate request threads deadlocked the whole backend-ai
process (confirmed live: a second request in flight during a chat
generation left even an unauthenticated ``GET /`` unresponsive). The
Qdrant query in between is cheap enough that holding the lock across
the whole function, rather than carving out just the two model calls,
isn't worth the extra complexity.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.indexing import embeddings
from app.model_lock import MODEL_LOCK
from app.retrieval import context_selection, highlighting, hybrid_search, reranker
from app.retrieval.context_selection import Candidate
from app.retrieval.schemas import SearchRequest, SearchResponse, SourceResult

logger = logging.getLogger(__name__)


def run_search(request: SearchRequest) -> SearchResponse:
    with MODEL_LOCK:
        return _run_search(request)


def _run_search(request: SearchRequest) -> SearchResponse:
    top_k = request.top_k or settings.retrieval_initial_k
    final_k = request.final_k or settings.retrieval_default_final_k

    query_dense = embeddings.embed_query(request.query)
    query_sparse = embeddings.embed_sparse([request.query])[0]

    points = hybrid_search.search(
        query_dense=query_dense,
        query_sparse=query_sparse,
        organization_id=request.organization_id,
        limit=top_k,
    )

    if not points:
        return SearchResponse(
            query=request.query, results=[], retrieved_count=0, reranked_count=0
        )

    candidates = [
        Candidate(
            document_id=point.payload["document_id"],
            filename=point.payload["filename"],
            page_number=point.payload.get("page_number"),
            chunk_index=point.payload["chunk_index"],
            text=point.payload["text"],
            dense_vector=(point.vector or {}).get("dense") or [],
            fusion_score=point.score,
        )
        for point in points
    ]

    rerank_scores = reranker.rerank(request.query, [c.text for c in candidates])
    for candidate, score in zip(candidates, rerank_scores):
        candidate.rerank_score = score

    selected = context_selection.select(
        candidates,
        final_k=final_k,
        dedup_threshold=settings.retrieval_dedup_threshold,
    )

    results = [
        SourceResult(
            document_id=c.document_id,
            filename=c.filename,
            page_number=c.page_number,
            chunk_index=c.chunk_index,
            text=c.text,
            excerpt=highlighting.build_excerpt(request.query, c.text),
            score=c.fusion_score,
            rerank_score=c.rerank_score,
        )
        for c in selected
    ]

    return SearchResponse(
        query=request.query,
        results=results,
        retrieved_count=len(candidates),
        reranked_count=len(candidates),
    )

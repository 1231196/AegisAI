"""Hybrid vector + BM25 search (US-015, US-016).

Qdrant's native Query API fuses a dense-vector prefetch and a
sparse-vector (BM25) prefetch via Reciprocal Rank Fusion, so there's
no separate lexical index / search engine to run and maintain — the
same Qdrant collection Epic 3 already writes to serves both signals.
"""

from __future__ import annotations

from qdrant_client.http import models as qmodels

from app.config import settings
from app.indexing.vector_store import DENSE_VECTOR_NAME, SPARSE_VECTOR_NAME, get_client


def search(
    *,
    query_dense: list[float],
    query_sparse: qmodels.SparseVector,
    organization_id: str,
    limit: int,
) -> list[qmodels.ScoredPoint]:
    """Return up to ``limit`` candidates fused from dense + sparse
    retrieval, scoped to ``organization_id``. Dense vectors are
    returned on each point (``with_vectors``) — context selection
    (US-018) needs them to compute dedup similarity without a second
    round-trip.
    """
    client = get_client()
    org_filter = qmodels.Filter(
        must=[
            qmodels.FieldCondition(
                key="organization_id",
                match=qmodels.MatchValue(value=organization_id),
            )
        ]
    )
    response = client.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            qmodels.Prefetch(
                query=query_dense,
                using=DENSE_VECTOR_NAME,
                filter=org_filter,
                limit=limit,
            ),
            qmodels.Prefetch(
                query=query_sparse,
                using=SPARSE_VECTOR_NAME,
                filter=org_filter,
                limit=limit,
            ),
        ],
        query=qmodels.FusionQuery(fusion=qmodels.Fusion.RRF),
        query_filter=org_filter,
        limit=limit,
        with_payload=True,
        with_vectors=True,
    )
    return response.points

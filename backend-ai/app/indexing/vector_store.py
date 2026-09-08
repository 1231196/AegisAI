"""Qdrant integration (US-012, extended for Epic 4 hybrid search / US-016).

Single collection shared by every tenant, scoped via an
``organization_id`` payload field rather than one collection per
organisation — avoids collection sprawl and matches Qdrant's own
multi-tenancy guidance.

Each point carries two named vectors: ``dense`` (jina-embeddings-v3,
semantic similarity) and ``sparse`` (BM25-style, lexical match) — the
pairing hybrid search fuses at query time via Qdrant's native
``Prefetch`` + ``Fusion.RRF`` (see ``app/retrieval/hybrid_search.py``).

Point ids are deterministic (``uuid5`` of ``document_id:chunk_index``)
so re-indexing a document naturally overwrites its own prior points
rather than accumulating duplicates when the chunk count doesn't
change. When the chunk count *does* change (a smaller or larger
chunk set on reindex), ``service.py`` deletes all of a document's
points before upserting the new set so stale extras never linger.
"""

from __future__ import annotations

import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None

DENSE_VECTOR_NAME = "dense"
SPARSE_VECTOR_NAME = "sparse"


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _client


def _has_expected_schema(collection_info) -> bool:
    vectors = collection_info.config.params.vectors
    sparse_vectors = collection_info.config.params.sparse_vectors
    if not isinstance(vectors, dict) or DENSE_VECTOR_NAME not in vectors:
        return False
    if not sparse_vectors or SPARSE_VECTOR_NAME not in sparse_vectors:
        return False
    return True


def ensure_collection() -> None:
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        info = client.get_collection(settings.qdrant_collection)
        if _has_expected_schema(info):
            return
        # Epic 4 added named dense+sparse vectors; a collection created
        # by the earlier (dense-only, unnamed vector) Epic 3 schema
        # can't be altered in place. Safe to drop and recreate — this
        # is a dev-stage project with no production data to preserve.
        logger.warning(
            "Qdrant collection '%s' has an outdated schema (missing named "
            "dense/sparse vectors) — dropping and recreating.",
            settings.qdrant_collection,
        )
        client.delete_collection(settings.qdrant_collection)

    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={
            DENSE_VECTOR_NAME: qmodels.VectorParams(
                size=settings.embedding_dim,
                distance=qmodels.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            SPARSE_VECTOR_NAME: qmodels.SparseVectorParams(
                modifier=qmodels.Modifier.IDF,
            ),
        },
    )
    logger.info("created Qdrant collection '%s' (dense+sparse)", settings.qdrant_collection)


def _point_id(document_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{document_id}:{chunk_index}"))


def upsert_chunks(
    *,
    document_id: str,
    organization_id: str,
    filename: str,
    chunks: list[str],
    vectors: list[list[float]],
    page_numbers: list[int | None],
) -> None:
    if not chunks:
        return
    from app.indexing.embeddings import embed_sparse

    client = get_client()
    sparse_vectors = embed_sparse(chunks)
    points = [
        qmodels.PointStruct(
            id=_point_id(document_id, i),
            vector={
                DENSE_VECTOR_NAME: vector,
                SPARSE_VECTOR_NAME: sparse_vector,
            },
            payload={
                "document_id": document_id,
                "organization_id": organization_id,
                "filename": filename,
                "chunk_index": i,
                "page_number": page_number,
                "text": chunk,
            },
        )
        for i, (chunk, vector, sparse_vector, page_number) in enumerate(
            zip(chunks, vectors, sparse_vectors, page_numbers)
        )
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def delete_document(document_id: str) -> None:
    client = get_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )

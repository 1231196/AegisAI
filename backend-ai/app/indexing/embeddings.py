"""Embedding generation: dense (US-011, jina-embeddings-v3) and sparse
(Epic 4 / US-016, fastembed BM25) — kept in one module since both are
"the embeddings the pipeline needs," used at both index-time (this
module's callers: ``indexing/vector_store.py``) and query-time
(``retrieval/service.py``). Splitting sparse embeddings into a
``retrieval``-only module would create a layering inversion, since
indexing needs it too (a chunk's sparse vector is computed once, at
upsert time).

Both models are lazily-created, process-wide singletons — model
instantiation is expensive (the dense model downloads/loads ~1GB of
weights) and far too slow to pay per-request.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)

# jina-embeddings-v3's native output is 1024-dim. Only pass
# ``truncate_dim`` to the model when a smaller size is actually
# requested (Matryoshka truncation) — omitting it in the common
# (native-size) case avoids depending on the exact kwarg shape a given
# sentence-transformers version expects for a no-op truncation.
_NATIVE_DIM = 1024


@lru_cache(maxsize=1)
def get_embedding_model():
    from sentence_transformers import SentenceTransformer

    kwargs: dict = {"trust_remote_code": True}
    if settings.embedding_dim != _NATIVE_DIM:
        kwargs["truncate_dim"] = settings.embedding_dim

    logger.info(
        "loading embedding model %s (dim=%d) - first call only, downloads "
        "model weights on first run",
        settings.embedding_model,
        settings.embedding_dim,
    )
    return SentenceTransformer(settings.embedding_model, **kwargs)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts for storage (the 'retrieval.passage'
    task — these are documents being indexed, not search queries)."""
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, task="retrieval.passage", show_progress_bar=False)
    return vectors.tolist()


def embed_query(query: str) -> list[float]:
    """Embed a single search query (US-015) — the 'retrieval.query'
    task, which jina-embeddings-v3 weights differently from
    'retrieval.passage' (asymmetric retrieval: queries are typically
    short questions, passages are long-form text)."""
    model = get_embedding_model()
    vectors = model.encode([query], task="retrieval.query", show_progress_bar=False)
    return vectors[0].tolist()


@lru_cache(maxsize=1)
def get_sparse_model():
    from fastembed import SparseTextEmbedding

    logger.info(
        "loading sparse embedding model %s - first call only, downloads "
        "model weights on first run",
        settings.sparse_model,
    )
    return SparseTextEmbedding(settings.sparse_model)


def embed_sparse(texts: list[str]) -> list:
    """BM25-style sparse embeddings (US-016) for hybrid search, ready to
    hand to Qdrant as ``SparseVector``s. Same function serves both
    index-time (chunks) and query-time (a single-item list) — BM25
    doesn't have the asymmetric query/passage distinction dense
    embedders do.
    """
    from qdrant_client.http import models as qmodels

    if not texts:
        return []
    model = get_sparse_model()
    return [
        qmodels.SparseVector(indices=emb.indices.tolist(), values=emb.values.tolist())
        for emb in model.embed(texts)
    ]

"""Cross-encoder reranking (US-017).

A cross-encoder scores each (query, candidate) pair jointly — much
more accurate than the bi-encoder similarity used for initial
retrieval, but too slow to run over a whole collection, hence the
two-stage design: cheap hybrid retrieval narrows to
``retrieval_initial_k`` candidates, then this reranks just those.

Multilingual (BAAI/bge-reranker-v2-m3) to match the multilingual
embedding model — an English-only reranker (e.g. ms-marco-MiniLM)
would undercut non-English queries even though retrieval found the
right candidates. Loads via plain ``sentence_transformers.CrossEncoder``
— no ``trust_remote_code`` custom modeling code, so none of the
embedding model's remote-code fragility applies here.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_reranker():
    from sentence_transformers import CrossEncoder

    logger.info(
        "loading reranker model %s - first call only, downloads model "
        "weights on first run",
        settings.reranker_model,
    )
    return CrossEncoder(settings.reranker_model, max_length=512)


def rerank(query: str, texts: list[str]) -> list[float]:
    """Score every (query, text) pair in one batched call. Returns
    scores in the same order as ``texts`` — higher is more relevant."""
    if not texts:
        return []
    model = get_reranker()
    pairs = [(query, text) for text in texts]
    scores = model.predict(pairs, show_progress_bar=False)
    return scores.tolist()

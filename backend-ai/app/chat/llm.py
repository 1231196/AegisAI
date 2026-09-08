"""Chat LLM client (Epic 5) — Google Gemini via langchain-google-genai.

Lazy, process-wide singleton, mirroring the pattern already used for
the embedding model (``app/indexing/embeddings.py``) and reranker
(``app/retrieval/reranker.py``) — model client construction is cheap
here (no weights to download, it's a thin HTTP client to the Gemini
API), but the singleton keeps the pattern consistent and avoids
re-validating the API key on every request.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_chat_model():
    from langchain_google_genai import ChatGoogleGenerativeAI

    logger.info("initialising chat model %s - first call only", settings.chat_model)
    return ChatGoogleGenerativeAI(
        model=settings.chat_model,
        google_api_key=settings.google_api_key,
    )

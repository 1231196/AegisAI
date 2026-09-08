"""Chat orchestrator (US-020..US-023): retrieve, then stream a RAG reply.

Runs synchronously in the request/response cycle, same as Epic 4's
search — the caller (backend-api) is proxying this stream straight
through to a waiting browser. Retrieval and generation are one
pipeline here (unlike Epic 4's backend-api -> backend-ai /search hop,
this reuses ``app.retrieval.service.run_search`` in-process — no
extra network round-trip for something already living in this
codebase).
"""

from __future__ import annotations

import json
import logging
from typing import Iterator

from app.chat.llm import get_chat_model
from app.chat.prompt import build_messages
from app.chat.schemas import ChatRequest
from app.retrieval.schemas import SearchRequest
from app.retrieval.service import run_search

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n".encode("utf-8")


def stream_chat_response(request: ChatRequest) -> Iterator[bytes]:
    search_response = run_search(
        SearchRequest(query=request.query, organization_id=request.organization_id)
    )

    yield _sse(
        "sources",
        {"results": [r.model_dump() for r in search_response.results]},
    )

    messages = build_messages(
        request.query,
        [{"role": m.role, "content": m.content} for m in request.history],
        search_response.results,
    )

    model = get_chat_model()
    for chunk in model.stream(messages):
        text = chunk.content if isinstance(chunk.content, str) else ""
        if text:
            yield _sse("token", {"text": text})

    yield _sse("done", {})

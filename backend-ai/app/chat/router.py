"""HTTP surface for chat (US-020..US-023).

Internal-only — backend-api is the sole caller, gated by the same
shared-secret dependency already defined for the indexing/retrieval
endpoints (reused here, not duplicated).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.chat.schemas import ChatRequest
from app.chat.service import stream_chat_response
from app.indexing.router import require_internal_token

router = APIRouter(tags=["chat"])


@router.post("/chat", dependencies=[Depends(require_internal_token)])
def chat(payload: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_response(payload), media_type="text/event-stream"
    )

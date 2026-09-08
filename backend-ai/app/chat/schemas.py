"""Request schema for the internal chat API (Epic 5)."""

from __future__ import annotations

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    """Body of POST /chat — sent only by backend-api. ``history`` holds
    prior turns only; the new turn is ``query``, kept separate so the
    prompt builder can't accidentally duplicate the current message."""

    query: str
    organization_id: str
    history: list[ChatMessage] = []

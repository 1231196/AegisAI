"""Pydantic schemas for the conversation/message endpoints (Epic 5)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConversationOut(BaseModel):
    id: str
    organization_id: str
    user_id: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources_json: str | None = None
    created_at: datetime


class SendMessageRequest(BaseModel):
    """Body of POST /conversations/{id}/messages."""

    content: str = Field(min_length=1, max_length=8000)

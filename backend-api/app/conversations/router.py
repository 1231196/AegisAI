"""Conversation router (Epic 5 / US-020..US-023).

Permission gate: caller must hold ``use_chat`` (staff) or ``chat``
(customer) — the two existing permission-catalog entries for chat
access. Every current role has one or the other; the gate is real for
any future role that has neither.

Ownership is strictly per-user: a conversation is only visible to (and
deletable by) the user who created it — this is personal chat history
("so I can continue my work"), not an org-wide resource, so there's no
admin-oversight listing here (mirrors Epic 4's decision not to add an
unrequested cross-tenant search).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.auth.dependencies import get_current_user
from app.auth.permissions import has_permission
from app.config import settings
from app.conversations.repositories import ConversationRepository, MessageRepository
from app.conversations.schemas import ConversationOut, MessageOut, SendMessageRequest
from app.documents.ai_client import SearchServiceError, stream_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])

_TITLE_MAX_LENGTH = 60


def require_chat_access(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role") or ""
    if not (has_permission(role, "use_chat") or has_permission(role, "chat")):
        logger.warning("authorisation failure: role '%s' has no chat permission", role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorised for this action",
        )
    return current_user


def _to_conversation_out(record: dict) -> ConversationOut:
    return ConversationOut(**record)


def _to_message_out(record: dict) -> MessageOut:
    return MessageOut(**record)


def _conversation_or_404(conversation_id: str, current_user: dict) -> dict:
    record = ConversationRepository.get_by_id(conversation_id)
    if record is None or record["user_id"] != current_user["id"]:
        # Foreign/missing conversation: 404 either way, so a probe
        # can't tell "doesn't exist" from "exists but isn't yours".
        raise HTTPException(status_code=404, detail="Conversation not found")
    return record


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    current_user: dict = Depends(require_chat_access),
) -> ConversationOut:
    record = ConversationRepository.create(
        organization_id=current_user["organization_id"],
        user_id=current_user["id"],
    )
    return _to_conversation_out(record)


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current_user: dict = Depends(require_chat_access),
) -> list[ConversationOut]:
    records = ConversationRepository.list_for_user(current_user["id"])
    return [_to_conversation_out(r) for r in records]


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: str,
    current_user: dict = Depends(require_chat_access),
) -> list[MessageOut]:
    _conversation_or_404(conversation_id, current_user)
    records = MessageRepository.list_for_conversation(conversation_id)
    return [_to_message_out(r) for r in records]


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_chat_access),
) -> None:
    _conversation_or_404(conversation_id, current_user)
    ConversationRepository.delete(conversation_id)
    return None


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: dict = Depends(require_chat_access),
) -> StreamingResponse:
    """Send a message and stream the assistant's RAG-generated reply
    (US-020, US-021).

    The user message is persisted immediately. The assistant message
    is persisted once the stream ends — or, via the generator's
    ``finally``, with whatever text was generated so far if the client
    disconnects mid-stream or backend-ai becomes unreachable, so a
    closed tab never silently loses the answer or leaves the user's
    message hanging with no reply at all.
    """
    conversation = _conversation_or_404(conversation_id, current_user)

    # Fetch history BEFORE persisting the new user message — it must
    # contain only *prior* turns. ``stream_chat`` takes the new query
    # as its own argument, so a history that already included it would
    # duplicate the current turn in the prompt.
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in MessageRepository.list_recent_for_conversation(
            conversation_id, settings.chat_history_max_messages
        )
    ]

    MessageRepository.create(
        conversation_id=conversation_id, role="user", content=payload.content
    )
    if conversation["title"] is None:
        ConversationRepository.update(
            conversation_id, title=payload.content[:_TITLE_MAX_LENGTH]
        )

    def event_stream():
        collected_text: list[str] = []
        collected_sources: str | None = None
        try:
            for event, data in stream_chat(
                query=payload.content,
                organization_id=current_user["organization_id"],
                history=history,
            ):
                if event == "sources":
                    collected_sources = data
                elif event == "token":
                    try:
                        collected_text.append(json.loads(data)["text"])
                    except (ValueError, KeyError, TypeError):
                        pass
                yield f"event: {event}\ndata: {data}\n\n".encode("utf-8")
        except SearchServiceError as exc:
            error_payload = json.dumps({"message": str(exc)})
            yield f"event: error\ndata: {error_payload}\n\n".encode("utf-8")
        finally:
            ConversationRepository.touch(conversation_id)
            if collected_text or collected_sources:
                MessageRepository.create(
                    conversation_id=conversation_id,
                    role="assistant",
                    content="".join(collected_text),
                    sources_json=collected_sources,
                )

    return StreamingResponse(event_stream(), media_type="text/event-stream")

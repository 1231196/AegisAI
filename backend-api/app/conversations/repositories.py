"""Repositories for conversations and messages (Epic 5).

Same shape as ``app.documents.repositories``: classmethods that open a
short-lived transactional session via ``app.db.session.session_scope``
and return plain dicts so routers never touch the ORM directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete as sql_delete, select

from app.db.models import Conversation, Message
from app.db.session import session_scope


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _conversation_to_dict(record: Conversation) -> dict:
    return {
        "id": record.id,
        "organization_id": record.organization_id,
        "user_id": record.user_id,
        "title": record.title,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


def _message_to_dict(record: Message) -> dict:
    return {
        "id": record.id,
        "conversation_id": record.conversation_id,
        "role": record.role,
        "content": record.content,
        "sources_json": record.sources_json,
        "created_at": record.created_at,
    }


class ConversationRepository:
    """SQL-backed conversation store."""

    @classmethod
    def create(cls, *, organization_id: str, user_id: str) -> dict:
        record = Conversation(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            user_id=user_id,
            title=None,
        )
        with session_scope() as session:
            session.add(record)
            session.flush()
            session.refresh(record)
            return _conversation_to_dict(record)

    @classmethod
    def get_by_id(cls, conversation_id: str) -> Optional[dict]:
        with session_scope() as session:
            record = session.get(Conversation, conversation_id)
            return _conversation_to_dict(record) if record is not None else None

    @classmethod
    def list_for_user(cls, user_id: str) -> list[dict]:
        with session_scope() as session:
            stmt = (
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
            )
            records = session.execute(stmt).scalars().all()
            return [_conversation_to_dict(r) for r in records]

    @classmethod
    def update(cls, conversation_id: str, **fields: object) -> Optional[dict]:
        with session_scope() as session:
            record = session.get(Conversation, conversation_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = _now()
            session.flush()
            return _conversation_to_dict(record)

    @classmethod
    def touch(cls, conversation_id: str) -> None:
        """Bump ``updated_at`` with no other field change — called when
        a new message lands, so ``list_for_user``'s "most recently
        active first" ordering reflects chat activity, not just
        conversation creation/rename time."""
        with session_scope() as session:
            record = session.get(Conversation, conversation_id)
            if record is not None:
                record.updated_at = _now()
                session.flush()

    @classmethod
    def delete(cls, conversation_id: str) -> bool:
        with session_scope() as session:
            record = session.get(Conversation, conversation_id)
            if record is None:
                return False
            session.execute(
                sql_delete(Message).where(Message.conversation_id == conversation_id)
            )
            session.delete(record)
        return True

    @classmethod
    def clear(cls) -> None:
        """Wipe every conversation (and message) row. Used by the
        autouse pytest fixture."""
        with session_scope() as session:
            session.execute(sql_delete(Message))
            session.execute(sql_delete(Conversation))


class MessageRepository:
    """SQL-backed message store."""

    @classmethod
    def create(
        cls,
        *,
        conversation_id: str,
        role: str,
        content: str,
        sources_json: Optional[str] = None,
    ) -> dict:
        record = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources_json=sources_json,
        )
        with session_scope() as session:
            session.add(record)
            session.flush()
            session.refresh(record)
            return _message_to_dict(record)

    @classmethod
    def list_for_conversation(cls, conversation_id: str) -> list[dict]:
        with session_scope() as session:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
            )
            records = session.execute(stmt).scalars().all()
            return [_message_to_dict(r) for r in records]

    @classmethod
    def list_recent_for_conversation(cls, conversation_id: str, limit: int) -> list[dict]:
        """Most recent ``limit`` messages, in chronological order —
        used to build the LLM's conversation-history context without
        loading a long conversation's entire history."""
        with session_scope() as session:
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            records = session.execute(stmt).scalars().all()
            return [_message_to_dict(r) for r in reversed(records)]

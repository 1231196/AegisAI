"""Repository for knowledge-base document metadata (Epic 3).

Same shape as ``app.auth.repositories.UserRepository``: classmethods
that open a short-lived transactional session via
``app.db.session.session_scope`` and return plain dicts so routers
never touch the ORM directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete as sql_delete, select

from app.db.models import Document
from app.db.session import session_scope


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _to_dict(record: Document) -> dict:
    return {
        "id": record.id,
        "organization_id": record.organization_id,
        "uploaded_by": record.uploaded_by,
        "filename": record.filename,
        "file_type": record.file_type,
        "size_bytes": record.size_bytes,
        "status": record.status,
        "chunk_count": record.chunk_count,
        "storage_path": record.storage_path,
        "content_hash": record.content_hash,
        "error_message": record.error_message,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "indexed_at": record.indexed_at,
    }


class DocumentRepository:
    """SQL-backed document metadata store."""

    @classmethod
    def create(
        cls,
        *,
        organization_id: str,
        uploaded_by: str,
        filename: str,
        file_type: str,
        size_bytes: int,
        storage_path: str,
        status: str = "processing",
    ) -> dict:
        record = Document(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            uploaded_by=uploaded_by,
            filename=filename,
            file_type=file_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            status=status,
        )
        with session_scope() as session:
            session.add(record)
            session.flush()
            # ``created_at``/``updated_at`` are ``server_default``
            # columns — refresh so the dict returned to the caller
            # (and serialised straight into ``DocumentOut``) has the
            # DB-generated timestamps rather than None. ``Document``
            # is the first model with server-side defaults; the other
            # repositories don't need this.
            session.refresh(record)
            return _to_dict(record)

    @classmethod
    def get_by_id(cls, document_id: str) -> Optional[dict]:
        with session_scope() as session:
            record = session.get(Document, document_id)
            return _to_dict(record) if record is not None else None

    @classmethod
    def list_in_organization(cls, organization_id: str) -> list[dict]:
        with session_scope() as session:
            stmt = (
                select(Document)
                .where(Document.organization_id == organization_id)
                .order_by(Document.created_at.desc())
            )
            records = session.execute(stmt).scalars().all()
            return [_to_dict(r) for r in records]

    @classmethod
    def list_all(cls) -> list[dict]:
        """Every document across every organisation. Platform-admin scope."""
        with session_scope() as session:
            stmt = select(Document).order_by(Document.created_at.desc())
            records = session.execute(stmt).scalars().all()
            return [_to_dict(r) for r in records]

    @classmethod
    def update(cls, document_id: str, **fields: object) -> Optional[dict]:
        with session_scope() as session:
            record = session.get(Document, document_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            record.updated_at = _now()
            session.flush()
            return _to_dict(record)

    @classmethod
    def mark_indexed(
        cls,
        document_id: str,
        *,
        chunk_count: int,
        content_hash: str,
    ) -> Optional[dict]:
        """Terminal-success transition. Sets ``indexed_at`` server-side
        (unlike the generic ``update``) so every success path stamps it
        consistently — including the "unchanged, skipped re-embedding"
        case (US-013), which still counts as a successful reindex.
        """
        return cls.update(
            document_id,
            status="indexed",
            chunk_count=chunk_count,
            content_hash=content_hash,
            error_message=None,
            indexed_at=_now(),
        )

    @classmethod
    def mark_failed(cls, document_id: str, *, error_message: str) -> Optional[dict]:
        return cls.update(document_id, status="failed", error_message=error_message)

    @classmethod
    def delete(cls, document_id: str) -> bool:
        with session_scope() as session:
            record = session.get(Document, document_id)
            if record is None:
                return False
            session.delete(record)
        return True

    @classmethod
    def clear(cls) -> None:
        """Wipe every document row. Used by the autouse pytest fixture."""
        with session_scope() as session:
            session.execute(sql_delete(Document))

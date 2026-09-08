"""ORM models for backend-api.

These mirror the dict-shape previously held in ``repositories.py`` so
the existing router code that consumes ``UserRepository.get_by_*()``
return values via ``user["..."]`` keeps working unchanged.

Schema choices
--------------
* ``id`` is a 36-char string (UUID4 hex+hyphens) rather than a native
  Postgres UUID column. Keeping it as a string keeps the SQL dialect
  portable (Postgres in prod, SQLite in tests) and matches what the
  API contract already returns.
* ``username`` is unique. ``organizations.slug`` is unique. The router
  pre-checks ``username_exists`` and returns 409 on the fast path; the
  unique index is the source of truth for racing inserts.
* ``disabled`` is a real boolean rather than a string flag. SQLite and
  Postgres both store it as INTEGER 0/1 transparently.
* Foreign key on ``users.organization_id`` enforces referential
  integrity. SQLite needs ``PRAGMA foreign_keys=ON`` per connection,
  which SQLAlchemy does not enable by default — see ``session.py``
  event hook.
"""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
    func,
)

from app.db.session import Base, engine


class Organization(Base):
    """Default organization + future tenant rows."""

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True)
    name = Column(String(128), nullable=False)
    slug = Column(String(64), nullable=False, unique=True)


class User(Base):
    """Auth identity row. ``password_hash`` is bcrypt; never returned by
    the Pydantic ``UserOut`` schema.
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(64), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False)
    organization_id = Column(
        String(36),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    disabled = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        # List-by-org is the hot path for the admin /users GET endpoint.
        Index("ix_users_organization_id", "organization_id"),
    )


class Document(Base):
    """Knowledge-base document metadata row (Epic 3 / US-008..US-014).

    This table is the source of truth for "what documents exist and
    what state are they in" — the actual extracted text, chunks, and
    embeddings never touch Postgres; they live in Qdrant, owned by
    backend-ai. ``storage_path`` points at the raw uploaded file on
    the ``documents-data`` volume shared with backend-ai (see
    docker-compose.yml), so reindexing doesn't require re-uploading.

    ``status`` lifecycle: ``processing`` -> ``indexed`` | ``failed``.
    backend-ai reports the terminal state via the internal callback
    endpoint (``PATCH /internal/documents/{id}/status``), never the
    user-facing router directly.

    ``content_hash`` (sha256 of the file bytes) is what makes
    reindexing incremental (US-013): backend-api sends the *previous*
    hash along with a reindex request, and backend-ai skips
    re-embedding entirely when the file hasn't changed.
    """

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    organization_id = Column(
        String(36),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(16), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    status = Column(String(16), nullable=False, default="processing")
    chunk_count = Column(Integer, nullable=True)
    storage_path = Column(String(512), nullable=False)
    content_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    indexed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # List-by-org is the hot path for GET /documents.
        Index("ix_documents_organization_id", "organization_id"),
    )


class Conversation(Base):
    """A chat session (Epic 5 / US-023).

    Strictly owned by ``user_id`` — conversations are personal history
    ("so I can continue my work"), not an org-wide shared resource, so
    there's no admin-oversight listing in this pass. ``title`` starts
    NULL and is set from the first user message once one arrives
    (``app.conversations.router``).
    """

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True)
    organization_id = Column(
        String(36),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # List-by-user is the hot path for GET /conversations.
        Index("ix_conversations_user_id", "user_id"),
    )


class Message(Base):
    """One turn in a conversation (Epic 5 / US-020, US-022).

    ``sources_json`` is a JSON-encoded list of the retrieval results
    (Epic 4's ``SourceResult`` shape) the assistant's answer was
    grounded in — NULL for user messages, populated for assistant
    messages once the stream finishes. Kept as a plain Text column
    (not a JSON column type) so SQLite and Postgres behave identically
    — the API layer is the only thing that ever needs to parse it.
    """

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id"),
        nullable=False,
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    sources_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        # List-by-conversation, ordered by created_at, is the hot path
        # for GET /conversations/{id}/messages.
        Index("ix_messages_conversation_id", "conversation_id"),
    )


# SQLite ships with foreign keys disabled by default, which would let
# tests create a user before its organization exists. The Postgres path
# enforces FK at the server level so this hook must NOT be wired
# unconditionally — ``PRAGMA foreign_keys=ON`` is SQLite-specific syntax
# and raises a syntax error against Postgres inside an open transaction.
# That error previously poisoned every connection from the pool: the
# bare ``except`` below silently swallowed it, leaving the next
# SQLAlchemy SELECT to die with ``InFailedSqlTransaction``. Gating the
# PRAGMA on the dialect name keeps the SQLite test path fast-correct
# while letting real Postgres connection errors fail loudly instead of
# crashing uvicorn inside ``Base.metadata.create_all`` at import time.
@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if engine.dialect.name == "sqlite":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

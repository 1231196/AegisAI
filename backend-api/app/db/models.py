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

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, event

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

"""Repositories for users, organisations, and refresh tokens.

User and Organization records are persisted to the SQL database
configured via ``settings.database_url`` (Postgres in production,
SQLite for the pytest default). The classmethod-shaped API on
``UserRepository`` and ``OrganizationRepository`` is preserved so
existing routers and tests depend only on:

* ``get_by_id(key) -> Optional[dict]``
* ``get_by_username(name) -> Optional[dict]``
* ``username_exists(name) -> bool``
* ``list_in_organization(org_id) -> list[dict]``
* ``create(...)/seed(...)/update(...)/delete(...)``
* ``clear()`` — wipes the rows (used by the autouse pytest fixture).

Each method opens a short-lived SQLAlchemy session via the
``_session`` context manager: one session == one transaction. Multi-step
atomicity (e.g. ``claim_for_rotation``) lives inside a single
repository method, so the family-sweep invariant is preserved.

``RefreshTokenRepository`` deliberately remains in-memory. Refresh tokens
are short-lived rotation state and Postgres would need a connection
pool warm-up just to mint a 7-day jti. We can migrate it to Redis in
a follow-up without touching the router layer.
"""

from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import RLock
from typing import Iterator, Optional

from sqlalchemy import delete as sql_delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models import Organization, User
from app.db.session import SessionLocal
from app.exceptions import ConflictError

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@contextmanager
def _session() -> Iterator:
    """Yield a transactional session; commit on success, rollback on error.

    Any exception (SQLAlchemy, network, programmer error) invalidates
    the transaction and triggers a rollback so the next checkout from
    the connection pool starts clean. ``BaseException`` subclasses like
    ``KeyboardInterrupt`` skip the rollback — Postgres aborts the tx
    server-side in that case, and rolling back an aborted-because-killed
    session can itself raise.

    The inner rollback is wrapped so that a *secondary* failure during
    rollback (e.g. a connection that's already been closed by the server
    or an ``InvalidRequestError`` on an already-rolled-back session) does
    not replace the original exception in ``__context__``. The original
    error remains visible to the caller; the swallowed secondary
    failure is logged at WARNING so an operator can correlate both
    events from a single log stream.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as primary:
        try:
            session.rollback()
        except Exception as secondary:
            logger.warning(
                "secondary failure during SQL rollback after primary error; "
                "swallowing so the original error surfaces: primary=%r secondary=%r",
                primary,
                secondary,
            )
        raise
    finally:
        try:
            session.close()
        except Exception:
            logger.warning("secondary failure during session.close()", exc_info=True)


def _user_to_dict(record: User) -> dict:
    """ORM ``User`` → plain dict matching the previous in-memory shape.

    Routers pull fields by key (``user["role"]`` etc.) and the Pydantic
    ``UserOut`` schema enumerates the public fields. The internal
    ``password_hash`` is intentionally kept on the dict because the
    router's ``login`` handler reads it for verification — outbound
    `UserOut` responses never include it.

    Caveat: this dict is built from a session-flushed but not-yet-committed
    row. If the surrounding ``_session`` commit fails (rare — e.g. a
    Postgres deadlock detected on flush), the caller has already seen
    this dict and the row never persisted. Repositories that need
    strict "only return on commit" semantics should re-fetch after the
    context-manager exits. Today's caller (``UserRepository.create``)
    pre-checks the unique constraint in the same transaction, so the
    race window is effectively closed.
    """
    return {
        "id": record.id,
        "username": record.username,
        "password_hash": record.password_hash,
        "role": record.role,
        "organization_id": record.organization_id,
        "disabled": bool(record.disabled),
    }


def _org_to_dict(record: Organization) -> dict:
    return {
        "id": record.id,
        "name": record.name,
        "slug": record.slug,
    }


class UserRepository:
    """SQL-backed user store. Public method shape is unchanged from
    the previous in-memory implementation so routers don't change.
    """

    @classmethod
    def seed(
        cls,
        *,
        id_: str,
        username: str,
        password_hash: str,
        role: str,
        organization_id: str,
        disabled: bool = False,
    ) -> dict:
        record = User(
            id=id_,
            username=username,
            password_hash=password_hash,
            role=role,
            organization_id=organization_id,
            disabled=disabled,
        )
        with _session() as session:
            session.add(record)
            session.flush()
            return _user_to_dict(record)

    @classmethod
    def create(
        cls,
        *,
        username: str,
        password_hash: str,
        role: str,
        organization_id: str,
        disabled: bool = False,
    ) -> dict:
        """Create a user. Single-transaction precheck + insert to close
        the TOCTOU race the previous two-call ``username_exists()`` then
        ``create()`` had between concurrent registrations for the same
        email. Raises ``ConflictError`` if the username exists; the
        :func:`app.main._conflict_exception_handler` translates that to
        HTTP 409.
        """
        with _session() as session:
            existing = session.execute(
                select(User.id).where(User.username == username)
            ).scalar_one_or_none()
            if existing is not None:
                raise ConflictError(
                    "An account with that email already exists",
                )
            record = User(
                id=str(uuid.uuid4()),
                username=username,
                password_hash=password_hash,
                role=role,
                organization_id=organization_id,
                disabled=disabled,
            )
            session.add(record)
            session.flush()
            return _user_to_dict(record)

    @classmethod
    def get_by_id(cls, user_id: str) -> Optional[dict]:
        with _session() as session:
            record = session.get(User, user_id)
            return _user_to_dict(record) if record is not None else None

    @classmethod
    def get_by_username(cls, username: str) -> Optional[dict]:
        with _session() as session:
            stmt = select(User).where(User.username == username)
            record = session.execute(stmt).scalar_one_or_none()
            return _user_to_dict(record) if record is not None else None

    @classmethod
    def username_exists(cls, username: str) -> bool:
        with _session() as session:
            stmt = select(User.id).where(User.username == username)
            return session.execute(stmt).scalar_one_or_none() is not None

    @classmethod
    def list_in_organization(cls, organization_id: str) -> list[dict]:
        with _session() as session:
            stmt = select(User).where(User.organization_id == organization_id)
            records = session.execute(stmt).scalars().all()
            return [_user_to_dict(record) for record in records]

    @classmethod
    def list_all(cls) -> list[dict]:
        """Every user across every organisation. Platform-admin scope.

        Used by ``GET /users`` when the caller's role is cross-tenant;
        otherwise the tenant-scoped ``list_in_organization`` path is
        used so the US-007 contract stays intact for plain admins.
        """
        with _session() as session:
            records = session.execute(select(User)).scalars().all()
            return [_user_to_dict(record) for record in records] 

    @classmethod
    def update(cls, user_id: str, **fields: object) -> Optional[dict]:
        with _session() as session:
            record = session.get(User, user_id)
            if record is None:
                return None
            for key, value in fields.items():
                setattr(record, key, value)
            session.flush()
            return _user_to_dict(record)

    @classmethod
    def delete(cls, user_id: str) -> bool:
        with _session() as session:
            record = session.get(User, user_id)
            if record is None:
                return False
            session.delete(record)
        # Cascade any active refresh tokens for this user. Refresh tokens
        # live in an in-memory store, so there is no FK to cascade.
        RefreshTokenRepository.revoke_all_for_user(user_id)
        return True

    @classmethod
    def clear(cls) -> None:
        """Wipe every user row. Used by the autouse pytest fixture."""
        with _session() as session:
            session.execute(sql_delete(User))


class OrganizationRepository:
    """SQL-backed organization store."""

    @classmethod
    def seed(cls, *, id_: str, name: str, slug: str) -> dict:
        record = Organization(id=id_, name=name, slug=slug)
        with _session() as session:
            session.add(record)
            session.flush()
            return _org_to_dict(record)

    @classmethod
    def create(cls, *, name: str, slug: str) -> dict:
        return cls.seed(id_=str(uuid.uuid4()), name=name, slug=slug)

    @classmethod
    def get_by_id(cls, org_id: str) -> Optional[dict]:
        with _session() as session:
            record = session.get(Organization, org_id)
            return _org_to_dict(record) if record is not None else None

    @classmethod
    def get_by_slug(cls, slug: str) -> Optional[dict]:
        with _session() as session:
            stmt = select(Organization).where(Organization.slug == slug)
            record = session.execute(stmt).scalar_one_or_none()
            return _org_to_dict(record) if record is not None else None

    @classmethod
    def list_all(cls) -> list[dict]:
        with _session() as session:
            records = session.execute(select(Organization)).scalars().all()
            return [_org_to_dict(record) for record in records]

    @classmethod
    def count_users(cls, org_id: str) -> int:
        """Number of users anchored to ``org_id``.

        Used by the DELETE /organizations/{id} before-delete guard so
        an operator must explicitly drain the org before removing it.
        Centralised here so routers/tests share one source of truth.
        """
        stmt = select(User.id).where(User.organization_id == org_id)
        with _session() as session:
            return len(session.execute(stmt).scalars().all())

    @classmethod
    def delete(cls, org_id: str) -> bool:
        """Remove an organisation row.

        Caller is responsible for the ``count_users > 0`` guard before
        calling — routers raise 400 in that case so the API gives a
        crisp error. The repository still defends itself: an FK
        constraint from ``users.organization_id`` will reject the
        DELETE if any users remain. Translate the resulting
        ``IntegrityError`` into the same ``ConflictError`` callers
        already know how to handle from ``UserRepository.create`` —
        that way a future caller (CLI script, test, agent mq) that
        forgets the pre-check still gets a clean 409 instead of a 500.
        """
        with _session() as session:
            record = session.get(Organization, org_id)
            if record is None:
                return False
            # SQLAlchemy 2.x defers the actual DELETE statement to
            # flush/commit. ``session.flush()`` is what runs the FK
            # check inline so ``IntegrityError`` is catchable here
            # (otherwise it would fire from the context manager's
            # ``session.commit()`` and bypass this handler).
            try:
                session.delete(record)
                session.flush()
            except IntegrityError as exc:
                raise ConflictError(
                    "Organization has active users; reassign "
                    "or delete the members first.",
                ) from exc
        return True

    @classmethod
    def clear(cls) -> None:
        """Wipe every organization row.

        Defensively clears ``users`` first so future callers don't need
        to remember the FK-correct order (users FK → organizations).
        Production callers seed fresh orgs afterwards.
        """
        with _session() as session:
            session.execute(sql_delete(User))
            session.execute(sql_delete(Organization))


class RefreshTokenRepository:
    """In-memory refresh-token store.

    Intentionally kept as a process-local dict: refresh tokens are
    short-lived rotation state and the router never needs to query them
    after revoking. The ``claim_for_rotation`` family-sweep invariant is
    enforced by the per-method lock below; multi-step atomicity lives
    inside ``claim_for_rotation`` so a single race window stays narrow.
    """

    _lock = RLock()
    _by_jti: dict[str, dict] = {}

    @classmethod
    def create(
        cls,
        *,
        jti: str,
        user_id: str,
        issued_at: datetime,
        expires_at: datetime,
    ) -> dict:
        record = {
            "jti": jti,
            "user_id": user_id,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "revoked_at": None,
            "replaced_by": None,
        }
        with cls._lock:
            cls._by_jti[jti] = record
            return record

    @classmethod
    def get(cls, jti: str) -> Optional[dict]:
        with cls._lock:
            return cls._by_jti.get(jti)

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        with cls._lock:
            record = cls._by_jti.get(jti)
            return record is not None and record["revoked_at"] is not None

    @classmethod
    def revoke(cls, jti: str) -> None:
        with cls._lock:
            record = cls._by_jti.get(jti)
            if record is not None and record["revoked_at"] is None:
                record["revoked_at"] = _now()

    @classmethod
    def claim_for_rotation(cls, old_jti: str, new_jti: str) -> bool:
        """Atomically rotate ``old_jti`` → ``new_jti``.

        Returns True iff this caller wins the rotation (i.e. ``old_jti``
        was still unclaimed at the moment of swap). Returns False when
        ``old_jti`` was already revoked — which is the rotation-race
        condition that signals potential token theft.
        """
        with cls._lock:
            record = cls._by_jti.get(old_jti)
            if record is None or record["revoked_at"] is not None:
                return False
            record["revoked_at"] = _now()
            record["replaced_by"] = new_jti
            return True

    @classmethod
    def revoke_all_for_user(cls, user_id: str) -> int:
        with cls._lock:
            count = 0
            now = _now()
            for record in cls._by_jti.values():
                if record["user_id"] == user_id and record["revoked_at"] is None:
                    record["revoked_at"] = now
                    count += 1
            return count

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._by_jti.clear()

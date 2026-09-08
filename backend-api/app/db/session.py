"""SQLAlchemy engine + session factory for backend-api persistence.

We use the sync SQLAlchemy 2.0 API. ``pool_pre_ping=True`` validates
connections on checkout so a Postgres restart doesn't surface as stale
connection errors under load. ``autoflush=False`` keeps writes explicit;
``autocommit=False`` is the default and lets each repository method
commit on success / rollback on exception via the per-method session
context manager.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def session_scope() -> Iterator:
    """Yield a transactional session; commit on success, rollback on error.

    Shared by every repository module (``auth/repositories.py``,
    ``documents/repositories.py``, ...) so the commit/rollback/close
    semantics live in exactly one place. Originally private to
    ``auth/repositories.py``; extracted here once a second repository
    module needed the identical behaviour.

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

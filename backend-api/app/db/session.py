"""SQLAlchemy engine + session factory for backend-api persistence.

We use the sync SQLAlchemy 2.0 API. ``pool_pre_ping=True`` validates
connections on checkout so a Postgres restart doesn't surface as stale
connection errors under load. ``autoflush=False`` keeps writes explicit;
``autocommit=False`` is the default and lets each repository method
commit on success / rollback on exception via the per-method session
context manager.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

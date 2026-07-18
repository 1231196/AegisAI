"""Database package: SQLAlchemy engine, session factory, ORM models.

Tables are created eagerly at import time (``metadata.create_all`` is
idempotent — it creates only missing tables). Both the FastAPI
``lifespan`` path and the pytest suite rely on this side-effect, so
tests work without an explicit setup step.
"""

from app.db.models import Organization, User  # noqa: F401  (re-exported)
from app.db.session import Base, SessionLocal, engine

# Idempotent — safe to re-run on every boot.
Base.metadata.create_all(bind=engine)

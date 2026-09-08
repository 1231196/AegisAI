from __future__ import annotations

import logging

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    jwt_secret: str = "dev-only-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    # Short-lived access tokens; pairing with stateful refresh rotation
    # keeps the unauthorised-use window small even without an access-
    # token blocklist. See US-004.
    jwt_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # Database URL. Defaults to a local SQLite file so ``pytest`` works
    # out of the box. Production / docker-compose MUST set this to a
    # Postgres URL (``postgresql+psycopg://...``).
    database_url: str = "sqlite:///./aegisai.db"

    @field_validator("database_url")
    @classmethod
    def _ensure_psycopg_dialect(cls, value: str) -> str:
        """Force ``+psycopg`` driver prefix for plain Postgres URLs.

        SQLAlchemy 2.0 with the ``psycopg`` (v3) driver needs an
        explicit ``postgresql+psycopg://…`` URL; a bare
        ``postgresql://…`` makes SQLAlchemy look for ``psycopg2`` which
        is not installed in this project. Compose sets the bare prefix
        so this validator normalises it on load.
        """
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value[len("postgresql://"):]
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value[len("postgres://"):]
        return value

    # Demo user is only seeded when explicitly enabled, and only in
    # non-production environments. Production deployments MUST leave
    # this False.
    seed_demo_user: bool = False

    # --- Epic 3: Knowledge Base ingestion ---------------------------------
    # Local path where uploaded files are written. Defaults to a
    # project-relative directory (mirrors ``database_url``'s local
    # SQLite default) so tests/local dev don't try to mkdir at the
    # filesystem root; docker-compose overrides this to the
    # ``documents-data`` volume mount point shared with backend-ai, so
    # backend-ai can read the file by path rather than the bytes being
    # re-uploaded over HTTP.
    documents_storage_path: str = "./data/documents"
    # 25MB — generous for the PDF/DOCX/TXT/MD/CSV formats US-008 covers
    # without letting a single upload exhaust disk or block the event
    # loop for too long while buffering into memory.
    max_upload_size_bytes: int = 25 * 1024 * 1024
    ai_backend_url: str = "http://backend-ai:8001"
    # Shared secret for the backend-api <-> backend-ai service-to-service
    # calls (see app.documents.internal_auth). Never a user JWT.
    internal_service_token: str = "dev-only-internal-token-change-me"

    # --- Epic 5: Chat -------------------------------------------------
    # How many of a conversation's most recent messages to send to the
    # LLM as context for a new reply. Mirrors backend-ai's identically-
    # named setting conceptually — kept here too since backend-api is
    # the one that fetches history from Postgres and hands it over.
    chat_history_max_messages: int = 10

    _DEFAULT_SECRET = "dev-only-secret-change-me-in-production"
    _DEFAULT_INTERNAL_TOKEN = "dev-only-internal-token-change-me"

    @model_validator(mode="after")
    def _refuse_unsafe_defaults_in_production(self) -> Settings:
        env = self.environment.lower()
        if env == "production":
            if self.jwt_secret == self._DEFAULT_SECRET:
                raise ValueError(
                    "JWT_SECRET must be set explicitly when ENVIRONMENT=production. "
                    "The default development secret is forbidden in production."
                )
            if self.internal_service_token == self._DEFAULT_INTERNAL_TOKEN:
                raise ValueError(
                    "INTERNAL_SERVICE_TOKEN must be set explicitly when "
                    "ENVIRONMENT=production. The default development value "
                    "is forbidden in production."
                )
            if self.seed_demo_user:
                raise ValueError(
                    "SEED_DEMO_USER must be disabled when ENVIRONMENT=production. "
                )
            if not self.database_url.startswith("postgresql"):
                raise ValueError(
                    "DATABASE_URL must be a Postgres URL when "
                    "ENVIRONMENT=production. The SQLite default is for "
                    "dev/test only.",
                )
        if env != "development" and self.jwt_secret == self._DEFAULT_SECRET:
            logger.warning(
                "Using default JWT secret in %s. Set JWT_SECRET to a strong "
                "random value before exposing this service.",
                env,
            )
        return self


settings = Settings()

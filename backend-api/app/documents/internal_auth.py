"""Service-to-service auth for the backend-ai -> backend-api callback.

The status-update endpoint (``PATCH /internal/documents/{id}/status``)
is called by backend-ai, not a logged-in user, so it can't go through
``require_role``/``require_permission`` (there is no user JWT). Instead
both services share one secret (``INTERNAL_SERVICE_TOKEN``, identical
env var on both containers) passed via the ``X-Internal-Token`` header.

This is deliberately a flat shared-secret check, not a JWT — it's an
internal network hop between two trusted services on the same Docker
network, not a user-facing credential.
"""

from __future__ import annotations

import hmac
import logging

from fastapi import Header, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    if x_internal_token is None or not hmac.compare_digest(
        x_internal_token, settings.internal_service_token
    ):
        logger.warning("internal-callback auth failure: missing or invalid X-Internal-Token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token",
        )

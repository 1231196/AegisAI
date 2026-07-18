"""FastAPI dependencies for authentication and authorisation.

Three building blocks:

* ``get_bearer_token`` — pulls the raw token out of the ``Authorization``
  header (or raises 401 with ``WWW-Authenticate: Bearer``).
* ``get_current_user`` — verifies the access JWT, resolves the user via
  the user repository, and returns the full user record.
* ``require_role(roles)`` — dependency factory that wraps
  ``get_current_user`` and 403s when the user's role is not in the
  supplied allow-list.

All three raise ``HTTPException`` directly so callers can rely on a
uniform 401/403 contract from any router that depends on them. Auth
failures are logged at WARNING with sanitised info (no token contents)
so brute-force and tenant-bypass attempts are observable in production.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.auth.permissions import has_permission
from app.auth.repositories import UserRepository
from app.auth.security import decode_access_token

logger = logging.getLogger(__name__)


def _bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract the bearer token portion of the Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[len("Bearer ") :].strip()


def get_bearer_token(authorization: Optional[str] = Header(default=None)) -> str:
    """Extract the bearer token from the Authorization header."""
    token = _bearer_token(authorization)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


def get_current_user(token: str = Depends(get_bearer_token)) -> dict:
    """Decode the access JWT and load the corresponding user record."""
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("auth failure: invalid or expired access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    uid = payload.get("uid")
    if not isinstance(uid, str) or not uid:
        logger.warning("auth failure: access token missing uid claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = UserRepository.get_by_id(uid)
    if user is None:
        logger.warning("auth failure: uid %s not found", uid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.get("disabled"):
        logger.warning("auth failure: disabled user %s attempted access", uid)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(allowed_roles: list[str]):
    """Dependency factory: 403 unless the user's role is in allowed_roles.

    Usage::

        @router.get(...)
        def handler(user: dict = Depends(require_role(["admin"])):
            ...
    """

    allowed = set(allowed_roles)

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed:
            logger.warning(
                "authorisation failure: role '%s' attempted action requiring %s",
                current_user.get("role"),
                sorted(allowed),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{current_user.get('role')}' is not authorised "
                    f"for this action"
                ),
            )
        return current_user

    return _check


def require_permission(permission: str):
    """Dependency factory: 403 unless the caller's role has ``permission``.

    Drop-in alternative to ``require_role`` for routers that want to
    gate against the permission catalog rather than enumerating role
    names. Same ``get_current_user`` base dependency — the auth
    contract is identical: missing/invalid token → 401, valid token but
    insufficient permission → 403.

    Usage::

        @router.get(...)
        def handler(user: dict = Depends(require_permission("manage_users"))):
            ...
    """

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        role = current_user.get("role")
        if not has_permission(role or "", permission):
            logger.warning(
                "authorisation failure: role '%s' missing permission '%s'",
                role,
                permission,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Role '{role}' is not authorised for this action"
                ),
            )
        return current_user

    return _check

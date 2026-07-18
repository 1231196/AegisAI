"""Pydantic schemas for the auth endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

# Canonical role set used across the codebase. Keep in sync with the
# ``require_role`` dependency and US-006 acceptance criteria.
#
# ``platform_admin`` is a cross-tenant operator scope: an account with
# this role can see/manage every organisation and every user across
# organisations. Plain ``admin`` remains tenant-isolated so the
# US-007 contract (and its test suite) is unchanged.
ROLES = frozenset({"platform_admin", "admin", "support_engineer", "customer"})

# Roles that bypass the per-tenant US-007 isolation checks on the
# user- and organisation-management routers. Centralised so routers
# stay declarative and the security contract is auditable in one place.
CROSS_TENANT_ROLES = frozenset({"platform_admin"})

def is_cross_tenant(role: str | None) -> bool:
    """True iff ``role`` is allowed to act across organisations."""
    return role in CROSS_TENANT_ROLES


class LoginRequest(BaseModel):
    """Credentials submitted to the login endpoint."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def _normalise_username(cls, value: str) -> str:
        """Strip whitespace and reject whitespace-only input.

        Without this, ``"   "`` would pass Pydantic's ``min_length=1``
        check (3 chars) and we'd then burn ~250 ms in a bcrypt call
        against the unreachable dummy hash. Failing fast here gives 422
        instead of a misleading 401.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("username must not be empty or whitespace-only")
        return stripped

    @field_validator("password")
    @classmethod
    def _no_whitespace_only_password(cls, value: str) -> str:
        """Reject whitespace-only passwords at validation time.

        We deliberately do NOT strip the password before bcrypt — a
        password is a secret and must never be silently normalised by
        the server.
        """
        if not value.strip():
            raise ValueError("password must not be empty or whitespace-only")
        return value


class TokenPair(BaseModel):
    """Bearer-token pair returned by ``/auth/login`` and ``/auth/refresh``."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access-token lifetime in seconds


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh."""

    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """Body of POST /auth/logout: revokes the named refresh token."""

    refresh_token: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    """Body of POST /auth/register: self-service signup for the demo.

    The field is called ``email`` to reflect the public surface; the
    user record stores it as ``username`` and ``created_at`` is owned by
    the repository. New users are scoped to the default organisation
    (created on demand) and assigned the ``customer`` role.
    """

    email: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        """Trim whitespace, require an @ symbol, lowercase for storage.

        We deliberately don't use a strict RFC-5322 regex; just enough
        validation to reject obvious garbage before bcrypt.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("email must not be empty or whitespace-only")
        if "@" not in stripped or " " in stripped:
            raise ValueError("must be a valid email address")
        return stripped.lower()


class UserOut(BaseModel):
    """Non-sensitive representation of a user."""

    id: str
    username: str
    role: str
    disabled: bool
    organization_id: str


class PermissionsResponse(BaseModel):
    """Response of ``GET /auth/me/permissions``.

    Returns the caller's role plus the canonical permission set
    derived from ``app.auth.permissions.ROLE_PERMISSIONS``. The SPA
    fetches this on hydration so role-aware UI rendering does not
    require hardcoding the catalog in two places.

    ``permissions`` is always a list (never None) — an unknown role
    resolves to an empty list so the front-end renders the "no
    permissions" empty state rather than crashing on null.
    """

    role: str
    permissions: list[str] = Field(default_factory=list)

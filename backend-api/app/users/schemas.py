"""Pydantic schemas for the user CRUD endpoints (US-005)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.auth.schemas import ROLES


class UserCreateRequest(BaseModel):
    """Body of POST /users (admin-only)."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: str
    organization_id: str = Field(min_length=1, max_length=64)
    disabled: bool = False

    @field_validator("username")
    @classmethod
    def _normalise_username(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("username must not be empty or whitespace-only")
        return stripped

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: str) -> str:
        if value not in ROLES:
            raise ValueError(f"role must be one of {sorted(ROLES)}")
        return value


class UserUpdateRequest(BaseModel):
    """Body of PATCH /users/{id}. All fields optional — partial update.

    ``organization_id`` is a separate field from create's
    ``organization_id`` because it's a *transfer*: the user moves
    from one organisation to another. Routers must (1) validate the
    target org exists and (2) revoke the user's refresh tokens so the
    next ``/auth/refresh`` mints a pair that reflects the new
    organisation. Leaving the existing access token (with the old
    org claim) untouched is acceptable — it expires within
    ``jwt_expire_minutes`` and the backend re-reads the user row on
    every request for the tenant check, so no security boundary is
    crossed.
    """

    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    role: Optional[str] = None
    disabled: Optional[bool] = None
    organization_id: Optional[str] = Field(default=None, min_length=1, max_length=64)

    @field_validator("role")
    @classmethod
    def _valid_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if value not in ROLES:
            raise ValueError(f"role must be one of {sorted(ROLES)}")
        return value

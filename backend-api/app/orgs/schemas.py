"""Pydantic schemas for the organization endpoints (US-007)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class OrganizationCreateRequest(BaseModel):
    """Body of POST /organizations (admin-only)."""

    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=64)

    @field_validator("slug")
    @classmethod
    def _normalise_slug(cls, value: str) -> str:
        """Lowercase + strip. Slugs are URL-safe identifiers."""
        stripped = value.strip().lower()
        if not stripped:
            raise ValueError("slug must not be empty")
        return stripped


class OrganizationOut(BaseModel):
    """Outbound representation of an organization. No secret data."""

    id: str
    name: str
    slug: str

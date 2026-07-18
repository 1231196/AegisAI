"""Pytest bootstrap for backend-api tests.

Set ``SEED_DEMO_USER=true`` at module-load time (informational) and
provide function-scoped fixtures that:

* wipe all in-memory repositories and seed the canonical "Acme"
  organisation + admin ``demo`` user (autouse, runs before every test)
* expose factory fixtures for creating additional users / orgs
* expose an authenticated client helper that logs in via the public
  /auth/login endpoint and returns the authorisation headers + token pair
"""

from __future__ import annotations

import os

import bcrypt
import pytest

os.environ.setdefault("SEED_DEMO_USER", "true")

from app.auth.repositories import (  # noqa: E402  (must follow env var set)
    OrganizationRepository,
    RefreshTokenRepository,
    UserRepository,
)

DEMO_ORG_ID = "00000000-0000-0000-0000-000000000001"
DEMO_USER_ID = "00000000-0000-0000-0000-0000000000aa"


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _seed_canonical_world() -> None:
    UserRepository.clear()
    OrganizationRepository.clear()
    RefreshTokenRepository.clear()
    OrganizationRepository.seed(id_=DEMO_ORG_ID, name="Acme Corp", slug="acme")
    UserRepository.seed(
        id_=DEMO_USER_ID,
        username="demo",
        password_hash=_hash("testpassword"),
        role="admin",
        organization_id=DEMO_ORG_ID,
        disabled=False,
    )


@pytest.fixture(autouse=True)
def _seed_repositories():
    """Wipe and re-seed in-memory repositories before every test."""
    _seed_canonical_world()
    yield


@pytest.fixture
def seeded_organization():
    return OrganizationRepository.get_by_id(DEMO_ORG_ID)


def make_user(
    *,
    username: str,
    password: str,
    role: str,
    organization_id: str = DEMO_ORG_ID,
    disabled: bool = False,
) -> dict:
    """Create a user record directly in the in-memory repository."""
    return UserRepository.create(
        username=username,
        password_hash=_hash(password),
        role=role,
        organization_id=organization_id,
        disabled=disabled,
    )


def make_organization(*, name: str, slug: str) -> dict:
    return OrganizationRepository.create(name=name, slug=slug)


@pytest.fixture
def login_as():
    """Return a callable that logs a user in via /auth/login.

    The callable returns ``(headers, token_pair_dict)`` so callers can
    drive protected endpoints. The HTTP path is exercised end-to-end,
    which is what we want for our integration tests.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    def _login(username: str, password: str) -> tuple[dict, dict]:
        response = client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        headers = {
            "Authorization": f"Bearer {body['access_token']}",
        }
        return headers, body

    return _login

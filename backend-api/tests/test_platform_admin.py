"""Tests for the platform_admin role (cross-tenant organisations + users).

These tests ADD coverage for the new surface without touching the
existing US-007 admin contract — the autouse ``_seed_repositories``
fixture seeds a plain ``admin`` user (``demo``) so the pre-existing
``test_users.py`` and ``test_orgs.py`` continue to lock in tenant
isolation for non-platform-admin roles.
"""

from __future__ import annotations

import pytest
from conftest import DEMO_ORG_ID, make_organization, make_user
from fastapi.testclient import TestClient

from app.auth.repositories import UserRepository
from app.main import app

client = TestClient(app)


@pytest.fixture
def platform_admin() -> dict:
    """Promote the seeded ``demo`` user to ``platform_admin``.

    Returned as a dict so tests can use both ``record["id"]`` and the
    login helper. Affects only the existing row: no new user is
    created (keeps the autouse fixture idempotent).
    """
    record = UserRepository.get_by_username("demo")
    assert record is not None
    UserRepository.update(record["id"], role="platform_admin")
    return record  # type: ignore[return-value]


def _platform_admin_headers(login_as):
    # First arg ``demo`` already promoted in the ``platform_admin``
    # fixture. ``login_as`` re-hits /auth/login which signs a fresh
    # token whose ``role`` claim reflects the updated DB row.
    return login_as("demo", "testpassword")[0]


# ---------------------------------------------------------------------------
# Organisations: cross-tenant list + delete
# ---------------------------------------------------------------------------


def test_platform_admin_lists_all_organizations(login_as, platform_admin):
    other_org = make_organization(name="Other Co", slug="other")
    headers = _platform_admin_headers(login_as)
    response = client.get("/organizations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    slugs = sorted(o["slug"] for o in body)
    assert slugs == ["acme", "other"]
    # Cross-tenant GET by id also succeeds.
    fetch_other = client.get(f"/organizations/{other_org['id']}", headers=headers)
    assert fetch_other.status_code == 200
    assert fetch_other.json()["slug"] == "other"


def test_platform_admin_can_create_organization(login_as, platform_admin):
    headers = _platform_admin_headers(login_as)
    response = client.post(
        "/organizations",
        json={"name": "Beta Corp", "slug": "beta"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["slug"] == "beta"


def test_platform_admin_can_delete_empty_organization(login_as, platform_admin):
    empty_org = make_organization(name="Empty Co", slug="empty")
    headers = _platform_admin_headers(login_as)
    response = client.delete(f"/organizations/{empty_org['id']}", headers=headers)
    assert response.status_code == 204
    follow_up = client.get(f"/organizations/{empty_org['id']}", headers=headers)
    assert follow_up.status_code == 404


def test_platform_admin_delete_with_active_users_returns_400(
    login_as, platform_admin
):
    make_user(
        username="member",
        password="memberpassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _platform_admin_headers(login_as)
    response = client.delete(f"/organizations/{DEMO_ORG_ID}", headers=headers)
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    # Message includes the user count so operators know what to drain.
    assert "active user" in detail
    # Org stays put.
    follow_up = client.get(f"/organizations/{DEMO_ORG_ID}", headers=headers)
    assert follow_up.status_code == 200


def test_admin_cannot_delete_organization(login_as):
    """Plain ``admin`` gets 403 from DELETE — the endpoint is
    hard-gated to platform_admin via ``require_role``. The test also
    asserts the org is STILL present after the rejected call so a
    future regression where the gate relaxes and 200 slips through
    would still fail this test.
    """
    headers = login_as("demo", "testpassword")[0]
    response = client.delete(f"/organizations/{DEMO_ORG_ID}", headers=headers)
    assert response.status_code == 403
    # The org must still exist post-rejection.
    follow_up = client.get(f"/organizations/{DEMO_ORG_ID}", headers=headers)
    assert follow_up.status_code == 200
    assert follow_up.json()["id"] == DEMO_ORG_ID


# ---------------------------------------------------------------------------
# Users: cross-tenant list + foreign create + foreign read/transfer
# ---------------------------------------------------------------------------


def test_platform_admin_lists_users_across_orgs(login_as, platform_admin):
    other_org = make_organization(name="Other Co", slug="other")
    make_user(
        username="leaker",
        password="leakerpassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _platform_admin_headers(login_as)
    response = client.get("/users", headers=headers)
    assert response.status_code == 200
    usernames = sorted(u["username"] for u in response.json())
    assert usernames == ["demo", "leaker"]


def test_platform_admin_can_filter_users_by_organization(login_as, platform_admin):
    other_org = make_organization(name="Other Co", slug="other")
    make_user(
        username="leaker",
        password="leakerpassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _platform_admin_headers(login_as)
    response = client.get(
        f"/users?organization_id={other_org['id']}", headers=headers
    )
    assert response.status_code == 200
    usernames = [u["username"] for u in response.json()]
    assert usernames == ["leaker"]


def test_platform_admin_can_create_user_in_foreign_org(login_as, platform_admin):
    other_org = make_organization(name="Other Co", slug="other")
    headers = _platform_admin_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "bob@other.com",
            "password": "bobpassword1",
            "role": "admin",
            "organization_id": other_org["id"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == other_org["id"]


def test_platform_admin_can_get_user_in_foreign_org(login_as, platform_admin):
    other_org = make_organization(name="Other Co", slug="other")
    other_user = make_user(
        username="zoe",
        password="zoepassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _platform_admin_headers(login_as)
    response = client.get(f"/users/{other_user['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "zoe"


def test_platform_admin_can_transfer_user_to_other_org(
    login_as, platform_admin
):
    """PATCHing organization_id moves the user; the user's row is updated."""
    target_org = make_organization(name="Target Co", slug="target")
    member = make_user(
        username="nomad",
        password="nomadpassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _platform_admin_headers(login_as)
    response = client.patch(
        f"/users/{member['id']}",
        json={"organization_id": target_org["id"]},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["organization_id"] == target_org["id"]


def test_patch_transfer_rejects_unknown_organization(
    login_as, platform_admin
):
    """PATCH with a structurally invalid ``organization_id`` returns 400.

    Driving on the seeded ``demo`` user (now platform_admin via the
    fixture) so we get a real ``user_id``.
    """
    record = UserRepository.get_by_username("demo")
    assert record is not None
    headers = _platform_admin_headers(login_as)
    response = client.patch(
        f"/users/{record['id']}",
        json={"organization_id": "does-not-exist"},
        headers=headers,
    )
    assert response.status_code == 400


def test_patch_transfer_same_org_is_noop(login_as, platform_admin):
    """PATCHing organization_id to the user's current org must succeed
    without revoking the user's refresh tokens. A no-op write must not
    invalidate the user's session.
    """
    from app.auth.repositories import RefreshTokenRepository
    from app.auth.security import create_refresh_token

    record = UserRepository.get_by_username("demo")
    assert record is not None
    headers = _platform_admin_headers(login_as)

    # ``create_refresh_token`` calls ``RefreshTokenRepository.create``
    # internally → just one persisted jti per mint. The returned
    # ``RefreshToken`` named tuple exposes ``token``, ``expires_in``,
    # and ``jti``.
    refresh = create_refresh_token(
        user_id=record["id"],
        username=record["username"],
    )
    before_count = len(RefreshTokenRepository._by_jti)
    captured_jti = refresh.jti

    # No-op transfer: organization_id equal to current.
    response = client.patch(
        f"/users/{record['id']}",
        json={"organization_id": record["organization_id"]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["organization_id"] == record["organization_id"]
    # No refresh-token family-sweep on a no-op write: the captured
    # jti must still be unrevoked AND the reload-store count did
    # not grow.
    assert not RefreshTokenRepository.is_revoked(captured_jti)
    # The token we issued is still stored — i.e. no spurious revoke
    # nor a phantom re-issue.
    assert captured_jti in RefreshTokenRepository._by_jti
    assert len(RefreshTokenRepository._by_jti) == before_count


def test_admin_cannot_transfer_user_to_foreign_org(login_as):
    """Plain ``admin`` cannot move a user to another org — 403."""
    target_org = make_organization(name="Target Co", slug="target")
    member = make_user(
        username="alice",
        password="alicepassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = login_as("demo", "testpassword")[0]
    response = client.patch(
        f"/users/{member['id']}",
        json={"organization_id": target_org["id"]},
        headers=headers,
    )
    assert response.status_code == 403
    # Still in the original org.
    follow_up = client.get(f"/users/{member['id']}", headers=headers)
    assert follow_up.status_code == 200
    assert follow_up.json()["organization_id"] == DEMO_ORG_ID

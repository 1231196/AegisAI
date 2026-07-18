"""Tests for user CRUD (US-005), RBAC (US-006), and tenant isolation (US-007).

The tests use the conftest helpers:
* ``login_as`` — drives /auth/login via the public endpoint
* ``make_user`` / ``make_organization`` — direct repository writes for
  test setup (e.g. to seed a customer without the admin going through
  /users POST)
"""

from __future__ import annotations

import pytest
from conftest import (
    DEMO_ORG_ID,
    DEMO_USER_ID,
    make_organization,
    make_user,
)
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CUSTOMER_USERNAME = "alice"
CUSTOMER_PASSWORD = "alicepass1"


def _admin_headers(login_as):
    return login_as("demo", "testpassword")[0]


def _customer_headers(login_as):
    return login_as(CUSTOMER_USERNAME, CUSTOMER_PASSWORD)[0]


@pytest.fixture
def customer_user():
    """Seed a customer user inside Acme. Re-uses the autouse reset."""
    make_user(
        username=CUSTOMER_USERNAME,
        password=CUSTOMER_PASSWORD,
        role="customer",
        organization_id=DEMO_ORG_ID,
    )


# ---------------------------------------------------------------------------
# US-005 — CRUD
# ---------------------------------------------------------------------------


def test_admin_can_list_users_in_own_org(login_as):
    headers = _admin_headers(login_as)
    response = client.get("/users", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["username"] == "demo"
    assert body[0]["role"] == "admin"


def test_admin_can_create_user(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "bob",
            "password": "bobpassword1",
            "role": "support_engineer",
            "organization_id": DEMO_ORG_ID,
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "bob"
    assert body["role"] == "support_engineer"
    assert body["disabled"] is False
    assert "password_hash" not in body

    # And the new user can actually log in.
    login_resp = client.post(
        "/auth/login",
        json={"username": "bob", "password": "bobpassword1"},
    )
    assert login_resp.status_code == 200


def test_admin_can_get_user_in_own_org(login_as):
    headers = _admin_headers(login_as)
    response = client.get(f"/users/{DEMO_USER_ID}", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "demo"


def test_admin_can_update_password_and_role(login_as):
    headers = _admin_headers(login_as)
    response = client.patch(
        f"/users/{DEMO_USER_ID}",
        json={"role": "support_engineer", "disabled": True},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "support_engineer"
    assert body["disabled"] is True


def test_admin_can_delete_user(login_as):
    other = make_user(
        username="to-delete",
        password="deletepassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _admin_headers(login_as)
    response = client.delete(f"/users/{other['id']}", headers=headers)
    assert response.status_code == 204
    follow_up = client.get(f"/users/{other['id']}", headers=headers)
    assert follow_up.status_code == 404


def test_admin_cannot_delete_self(login_as):
    headers = _admin_headers(login_as)
    response = client.delete(f"/users/{DEMO_USER_ID}", headers=headers)
    assert response.status_code == 400
    assert "yourself" in response.json()["detail"].lower()


def test_patch_user_with_empty_body_returns_400(login_as):
    """An empty PATCH body must surface as a 400 \u2014 silently no-op'ing
    would hide client-side bugs that omit fields by mistake."""
    headers = _admin_headers(login_as)
    response = client.patch(f"/users/{DEMO_USER_ID}", json={}, headers=headers)
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    assert "no fields" in detail


def test_admin_cannot_create_duplicate_username(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "demo",
            "password": "newpassword1",
            "role": "customer",
            "organization_id": DEMO_ORG_ID,
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_admin_cannot_create_user_in_other_organization(login_as):
    other_org = make_organization(name="Other Co", slug="other")
    headers = _admin_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "bob",
            "password": "bobpassword1",
            "role": "customer",
            "organization_id": other_org["id"],
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_admin_creating_user_rejects_unknown_organization(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "bob",
            "password": "bobpassword1",
            "role": "customer",
            "organization_id": "does-not-exist",
        },
        headers=headers,
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# US-006 — RBAC: non-admins get 403 on admin-only endpoints
# ---------------------------------------------------------------------------


def test_customer_cannot_list_users(customer_user, login_as):
    headers = _customer_headers(login_as)
    response = client.get("/users", headers=headers)
    assert response.status_code == 403


def test_customer_cannot_create_user(customer_user, login_as):
    headers = _customer_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "eve",
            "password": "evepassword1",
            "role": "customer",
            "organization_id": DEMO_ORG_ID,
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_customer_cannot_delete_user(customer_user, login_as):
    headers = _customer_headers(login_as)
    response = client.delete(f"/users/{DEMO_USER_ID}", headers=headers)
    assert response.status_code == 403


def test_support_engineer_cannot_create_user(login_as):
    make_user(
        username="sue",
        password="suepassword1",
        role="support_engineer",
        organization_id=DEMO_ORG_ID,
    )
    headers, _ = login_as("sue", "suepassword1")
    response = client.post(
        "/users",
        json={
            "username": "frank",
            "password": "frankpassword1",
            "role": "customer",
            "organization_id": DEMO_ORG_ID,
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_user_role_must_be_one_of_three_enum_values(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/users",
        json={
            "username": "bob",
            "password": "bobpassword1",
            "role": "owner",  # not in ROLES
            "organization_id": DEMO_ORG_ID,
        },
        headers=headers,
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# US-007 — tenant isolation: admin in org A can't see/edit/delete users in org B
# ---------------------------------------------------------------------------


def test_admin_cannot_get_user_in_other_org(login_as):
    other_org = make_organization(name="Other Co", slug="other")
    other_user = make_user(
        username="zoe",
        password="zoepassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _admin_headers(login_as)
    response = client.get(f"/users/{other_user['id']}", headers=headers)
    assert response.status_code == 404


def test_admin_cannot_update_user_in_other_org(login_as):
    other_org = make_organization(name="Other Co", slug="other")
    other_user = make_user(
        username="yolanda",
        password="yolandapassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _admin_headers(login_as)
    response = client.patch(
        f"/users/{other_user['id']}",
        json={"disabled": True},
        headers=headers,
    )
    assert response.status_code == 404


def test_admin_cannot_delete_user_in_other_org(login_as):
    other_org = make_organization(name="Other Co", slug="other")
    other_user = make_user(
        username="xavier",
        password="xavierpassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _admin_headers(login_as)
    response = client.delete(f"/users/{other_user['id']}", headers=headers)
    assert response.status_code == 404


def test_list_users_does_not_leak_other_orgs(login_as):
    other_org = make_organization(name="Other Co", slug="other")
    make_user(
        username="leaker",
        password="leakerpassword1",
        role="admin",
        organization_id=other_org["id"],
    )
    headers = _admin_headers(login_as)
    response = client.get("/users", headers=headers)
    assert response.status_code == 200
    usernames = [u["username"] for u in response.json()]
    assert "leaker" not in usernames
    assert "demo" in usernames

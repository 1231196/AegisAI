"""Tests for organization endpoints (US-007)."""

from __future__ import annotations

from conftest import DEMO_ORG_ID, make_organization, make_user
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _admin_headers(login_as):
    return login_as("demo", "testpassword")[0]


def test_admin_lists_only_own_organization(login_as):
    make_organization(name="Other Co", slug="other")
    headers = _admin_headers(login_as)
    response = client.get("/organizations", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["slug"] == "acme"
    assert body[0]["id"] == DEMO_ORG_ID


def test_admin_can_create_organization(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/organizations",
        json={"name": "Beta Corp", "slug": "beta"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Beta Corp"
    assert body["slug"] == "beta"


def test_admin_cannot_create_duplicate_slug(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/organizations",
        json={"name": "Beta Duplicate", "slug": "acme"},
        headers=headers,
    )
    assert response.status_code == 409


def test_admin_cannot_get_organization_in_other_tenant(login_as):
    other_org = make_organization(name="Other Co", slug="other")
    headers = _admin_headers(login_as)
    response = client.get(f"/organizations/{other_org['id']}", headers=headers)
    assert response.status_code == 404


def test_admin_can_get_own_organization(login_as):
    headers = _admin_headers(login_as)
    response = client.get(f"/organizations/{DEMO_ORG_ID}", headers=headers)
    assert response.status_code == 200
    assert response.json()["slug"] == "acme"


def test_customer_cannot_list_organizations(login_as):
    make_user(
        username="zoe",
        password="zoepassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers, _ = login_as("zoe", "zoepassword1")
    response = client.get("/organizations", headers=headers)
    assert response.status_code == 403


def test_customer_cannot_create_organization(login_as):
    make_user(
        username="yann",
        password="yannpassword1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers, _ = login_as("yann", "yannpassword1")
    response = client.post(
        "/organizations",
        json={"name": "Yann's Co", "slug": "yanns-co"},
        headers=headers,
    )
    assert response.status_code == 403


def test_create_organization_rejects_empty_slug(login_as):
    headers = _admin_headers(login_as)
    response = client.post(
        "/organizations",
        json={"name": "Empty", "slug": "   "},
        headers=headers,
    )
    assert response.status_code == 422

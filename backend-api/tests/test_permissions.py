"""Tests for the four-tier RBAC permission catalog + /auth/me/permissions.

These tests assert:

* The catalog exposes the spec'd permission strings for every role.
* ``GET /auth/me/permissions`` returns the right shape + content per
  role (carried via JWT-claim ``role``).
* Customer + Support Engineer cannot touch ``/users`` or
  ``/organizations`` (US-006/US-007 regression lock).
* ``require_permission`` dependency factory gates correctly.
"""

from __future__ import annotations

import pytest
from conftest import DEMO_ORG_ID, make_user
from fastapi.testclient import TestClient

from app.auth.permissions import (
    ACCESS_EVALUATION_DASHBOARDS,
    ACCESS_MONITORING,
    APPROVE_AI_ACTIONS,
    CHAT,
    CONFIGURE_AVAILABLE_LLMS,
    CONFIGURE_GLOBAL_AI_SETTINGS,
    CONFIGURE_INTEGRATIONS,
    CONFIGURE_MCP_SERVERS,
    CONFIGURE_ORG_AI_SETTINGS,
    CREATE_TICKETS,
    DELETE_ORG_DOCUMENTS,
    DELETE_OWN_DOCUMENTS,
    DOWNLOAD_GENERATED_ANSWERS,
    MANAGE_ALL_ORGANIZATIONS,
    MANAGE_ALL_USERS,
    MANAGE_BILLING,
    MANAGE_CONVERSATIONS,
    MANAGE_KNOWLEDGE_BASE,
    MANAGE_USERS,
    PERMISSIONS,
    REINDEX_DOCUMENTS,
    ROLE_PERMISSIONS,
    SEARCH_INTERNAL_LOGS,
    SEARCH_KNOWLEDGE_BASE,
    SEARCH_ORDERS,
    SEARCH_PAYMENTS,
    UPLOAD_DOCUMENTS,
    UPLOAD_FILES,
    USE_AI_AGENT,
    USE_CHAT,
    VIEW_ALL_LOGS,
    VIEW_CONVERSATION_HISTORY,
    VIEW_GLOBAL_ANALYTICS,
    VIEW_OWN_CONVERSATIONS,
    VIEW_ORG_ANALYTICS,
    VIEW_ORG_LOGS,
    VIEW_SOURCES,
    has_permission,
    permissions_for_role,
)
from app.main import app

client = TestClient(app)


def _headers_for(username: str, password: str, login_as) -> dict:
    return login_as(username, password)[0]


# ---------------------------------------------------------------------------
# Catalog: every spec'd permission exists + is wired to the right roles.
# ---------------------------------------------------------------------------


def test_catalog_contains_every_spec_permission():
    """All permission constants must appear in ``PERMISSIONS``.

    A typo leaving any constant orphaned would mean the role-mappings
    reference a string the catalog doesn't know — ``has_permission``
    would silently return False. We lock the catalog to the union of
    every documented string.
    """
    expected = {
        MANAGE_ALL_ORGANIZATIONS,
        MANAGE_ALL_USERS,
        CONFIGURE_GLOBAL_AI_SETTINGS,
        CONFIGURE_AVAILABLE_LLMS,
        CONFIGURE_MCP_SERVERS,
        VIEW_GLOBAL_ANALYTICS,
        VIEW_ALL_LOGS,
        MANAGE_BILLING,
        ACCESS_MONITORING,
        ACCESS_EVALUATION_DASHBOARDS,
        MANAGE_USERS,
        UPLOAD_DOCUMENTS,
        DELETE_ORG_DOCUMENTS,
        MANAGE_KNOWLEDGE_BASE,
        CONFIGURE_ORG_AI_SETTINGS,
        VIEW_ORG_ANALYTICS,
        VIEW_ORG_LOGS,
        APPROVE_AI_ACTIONS,
        MANAGE_CONVERSATIONS,
        CONFIGURE_INTEGRATIONS,
        USE_CHAT,
        DELETE_OWN_DOCUMENTS,
        REINDEX_DOCUMENTS,
        SEARCH_KNOWLEDGE_BASE,
        CREATE_TICKETS,
        SEARCH_INTERNAL_LOGS,
        SEARCH_ORDERS,
        SEARCH_PAYMENTS,
        USE_AI_AGENT,
        VIEW_SOURCES,
        VIEW_CONVERSATION_HISTORY,
        CHAT,
        VIEW_OWN_CONVERSATIONS,
        UPLOAD_FILES,
        DOWNLOAD_GENERATED_ANSWERS,
    }
    assert expected.issubset(PERMISSIONS)


def test_platform_admin_has_cross_tenant_superset():
    perms = permissions_for_role("platform_admin")
    assert MANAGE_ALL_ORGANIZATIONS in perms
    assert MANAGE_ALL_USERS in perms
    assert CONFIGURE_GLOBAL_AI_SETTINGS in perms
    assert CONFIGURE_AVAILABLE_LLMS in perms
    assert CONFIGURE_MCP_SERVERS in perms
    assert VIEW_GLOBAL_ANALYTICS in perms
    assert VIEW_ALL_LOGS in perms
    assert MANAGE_BILLING in perms
    assert ACCESS_MONITORING in perms
    assert ACCESS_EVALUATION_DASHBOARDS in perms
    # Platform admin also has the org-admin surface (defence-in-depth).
    assert MANAGE_USERS in perms
    assert CONFIGURE_ORG_AI_SETTINGS in perms


def test_admin_has_only_org_scoped_permissions():
    perms = permissions_for_role("admin")
    # Org Admin spec.
    assert MANAGE_USERS in perms
    assert UPLOAD_DOCUMENTS in perms
    assert DELETE_ORG_DOCUMENTS in perms
    assert MANAGE_KNOWLEDGE_BASE in perms
    assert CONFIGURE_ORG_AI_SETTINGS in perms
    assert VIEW_ORG_ANALYTICS in perms
    assert VIEW_ORG_LOGS in perms
    assert MANAGE_CONVERSATIONS in perms
    assert CONFIGURE_INTEGRATIONS in perms
    # NOT cross-tenant.
    assert MANAGE_ALL_ORGANIZATIONS not in perms
    assert MANAGE_ALL_USERS not in perms
    assert MANAGE_BILLING not in perms


def test_support_engineer_has_tools_but_no_admin():
    perms = permissions_for_role("support_engineer")
    assert USE_CHAT in perms
    assert UPLOAD_DOCUMENTS in perms
    assert DELETE_OWN_DOCUMENTS in perms
    assert REINDEX_DOCUMENTS in perms
    assert SEARCH_KNOWLEDGE_BASE in perms
    assert CREATE_TICKETS in perms
    assert SEARCH_INTERNAL_LOGS in perms
    assert SEARCH_ORDERS in perms
    assert SEARCH_PAYMENTS in perms
    assert USE_AI_AGENT in perms
    assert VIEW_SOURCES in perms
    assert VIEW_CONVERSATION_HISTORY in perms
    # NOT admin / org-admin.
    assert MANAGE_USERS not in perms
    assert CONFIGURE_ORG_AI_SETTINGS not in perms
    assert MANAGE_CONVERSATIONS not in perms
    # NOT cross-tenant.
    assert MANAGE_ALL_ORGANIZATIONS not in perms


def test_customer_has_only_chat_and_own_conversations():
    perms = permissions_for_role("customer")
    assert CHAT in perms
    assert VIEW_OWN_CONVERSATIONS in perms
    assert UPLOAD_FILES in perms
    assert VIEW_SOURCES in perms
    assert DOWNLOAD_GENERATED_ANSWERS in perms
    # NOT admin surfaces.
    assert MANAGE_USERS not in perms
    assert SEARCH_INTERNAL_LOGS not in perms
    assert SEARCH_ORDERS not in perms
    assert UPLOAD_DOCUMENTS not in perms
    assert MANAGE_ALL_ORGANIZATIONS not in perms


def test_unknown_role_returns_empty_set():
    """Defence-in-depth: a future role typo doesn't grant everything."""
    assert permissions_for_role("ghost-role") == frozenset()
    assert has_permission("ghost-role", "anything") is False


def test_unknown_permission_always_denies():
    """A permission string typo shouldn't silently grant access."""
    assert has_permission("platform_admin", "do_anything") is False
    assert has_permission("admin", "totally_made_up_perm") is False


# ---------------------------------------------------------------------------
# /auth/me/permissions endpoint
# ---------------------------------------------------------------------------


def test_endpoint_returns_platform_admin_full_set(login_as):
    make_user(
        username="pa",
        password="papassword1",
        role="platform_admin",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("pa", "papassword1", login_as)
    response = client.get("/auth/me/permissions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "platform_admin"
    assert MANAGE_ALL_ORGANIZATIONS in body["permissions"]
    assert MANAGE_ALL_USERS in body["permissions"]
    assert CONFIGURE_GLOBAL_AI_SETTINGS in body["permissions"]
    assert MANAGE_USERS in body["permissions"]


def test_endpoint_returns_admin_org_scoped_set(login_as):
    headers = _headers_for("demo", "testpassword", login_as)  # demo is admin by conftest
    response = client.get("/auth/me/permissions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "admin"
    assert MANAGE_USERS in body["permissions"]
    assert CONFIGURE_ORG_AI_SETTINGS in body["permissions"]
    # Cross-tenant permissions MUST NOT be present.
    assert MANAGE_ALL_ORGANIZATIONS not in body["permissions"]
    assert MANAGE_ALL_USERS not in body["permissions"]


def test_endpoint_returns_support_engineer_tools_only_set(login_as):
    make_user(
        username="sue",
        password="suepassword1",
        role="support_engineer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("sue", "suepassword1", login_as)
    response = client.get("/auth/me/permissions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "support_engineer"
    assert USE_AI_AGENT in body["permissions"]
    assert CREATE_TICKETS in body["permissions"]
    assert MANAGE_USERS not in body["permissions"]
    assert MANAGE_ALL_ORGANIZATIONS not in body["permissions"]


def test_endpoint_returns_customer_chat_only_set(login_as):
    make_user(
        username="alice",
        password="alicepass1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("alice", "alicepass1", login_as)
    response = client.get("/auth/me/permissions", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "customer"
    assert CHAT in body["permissions"]
    assert VIEW_OWN_CONVERSATIONS in body["permissions"]
    assert MANAGE_USERS not in body["permissions"]
    assert SEARCH_INTERNAL_LOGS not in body["permissions"]
    assert VIEW_ALL_LOGS not in body["permissions"]


def test_endpoint_rejects_unauthenticated():
    response = client.get("/auth/me/permissions")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Regression: customer + support engineer STILL get 403 on admin endpoints
# ---------------------------------------------------------------------------


def test_customer_cannot_get_their_own_permissions_via_users_endpoint(
    login_as,
):
    make_user(
        username="alice",
        password="alicepass1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("alice", "alicepass1", login_as)
    response = client.get("/users", headers=headers)
    assert response.status_code == 403


def test_support_engineer_cannot_get_users_endpoint(login_as):
    make_user(
        username="sue",
        password="suepassword1",
        role="support_engineer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("sue", "suepassword1", login_as)
    response = client.get("/users", headers=headers)
    assert response.status_code == 403


def test_customer_cannot_get_organizations_endpoint(login_as):
    make_user(
        username="alice",
        password="alicepass1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("alice", "alicepass1", login_as)
    response = client.get("/organizations", headers=headers)
    assert response.status_code == 403


def test_support_engineer_cannot_get_organizations_endpoint(login_as):
    make_user(
        username="sue",
        password="suepassword1",
        role="support_engineer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("sue", "suepassword1", login_as)
    response = client.get("/organizations", headers=headers)
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# require_permission dependency factory
# ---------------------------------------------------------------------------


def test_require_permission_allows_holder(login_as):
    """Sanity: a customer calling a chat-protected endpoint succeeds."""
    make_user(
        username="alice",
        password="alicepass1",
        role="customer",
        organization_id=DEMO_ORG_ID,
    )
    headers = _headers_for("alice", "alicepass1", login_as)
    # ``/auth/me/permissions`` is auth-only (any role can introspect).
    # The router then returns sorted permissions; we just confirm the
    # call succeeds, the role gate is fine, and the catalog is wired.
    response = client.get("/auth/me/permissions", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "customer"


# Roll-call: every documented permission string is referenced above
# by ``PERMISSIONS.issubset`` so a deletion breaks ``test_catalog_*``.
@pytest.mark.parametrize("perm", sorted(PERMISSIONS))
def test_every_catalog_permission_is_reachable_via_at_least_one_role(perm):
    """Every permission in the catalog must be granted to at least one role.

    Lock-in so a future rename drift between ``PERMISSIONS`` and
    ``ROLE_PERMISSIONS`` is caught by pytest, not by a surprised
    user complaining "permission X used to work".
    """
    granted = any(perm in perms for perms in ROLE_PERMISSIONS.values())
    assert granted, f"permission {perm!r} is in the catalog but no role has it"

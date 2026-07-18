"""Permission catalog for the four-tier RBAC.

This is the single source of truth for "which role can do what?" in
AegisAI. The four roles map 1-to-1 with the product spec:

* ``platform_admin``  — Cross-tenant operator (Platform Admin / Super Admin).
* ``admin``           — Single-tenant org admin (Organization Admin).
* ``support_engineer`` — Internal staff operator (Support Engineer).
* ``customer``        — End-user (Customer).

Adding or renaming a permission is intentional and requires updating
both this file AND ``frontend/src/api/client.ts``'s ``PERMISSIONS``
mirror. The two stay in lock-step so the SPA can render role-aware UI
without synchronising against the backend on every step.

Why a string catalog at all?
----------------------------
The router layer already gates ``/users`` and ``/organizations`` with
``require_role(["admin","platform_admin"])`` (US-006 / US-007). The
catalog below is *additive*: future endpoints can call
``Depends(require_permission("manage_users"))`` instead of enumerating
role allow-lists, so the security contract stays declarative.

Operational permissions listed in the user spec ("configure LLMs",
"manage MCP servers", "manage billing") are present in the catalog so
the SPA can render their menu items and route stubs. **No router
exists for them yet** — those are follow-up work and the catalog is
the seam where they will plug in.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Permission constants — verbatim from the product spec.
# ---------------------------------------------------------------------------
# Platform Admin (Super Admin) — cross-tenant.
MANAGE_ALL_ORGANIZATIONS = "manage_all_organizations"
MANAGE_ALL_USERS = "manage_all_users"
CONFIGURE_GLOBAL_AI_SETTINGS = "configure_global_ai_settings"
CONFIGURE_AVAILABLE_LLMS = "configure_available_llms"
CONFIGURE_MCP_SERVERS = "configure_mcp_servers"
VIEW_GLOBAL_ANALYTICS = "view_global_analytics"
VIEW_ALL_LOGS = "view_all_logs"
MANAGE_BILLING = "manage_billing"  # future
ACCESS_MONITORING = "access_monitoring"
ACCESS_EVALUATION_DASHBOARDS = "access_evaluation_dashboards"

# Organization Admin — single-tenant.
MANAGE_USERS = "manage_users"
UPLOAD_DOCUMENTS = "upload_documents"
DELETE_ORG_DOCUMENTS = "delete_org_documents"
MANAGE_KNOWLEDGE_BASE = "manage_knowledge_base"
CONFIGURE_ORG_AI_SETTINGS = "configure_org_ai_settings"
VIEW_ORG_ANALYTICS = "view_org_analytics"
VIEW_ORG_LOGS = "view_org_logs"
APPROVE_AI_ACTIONS = "approve_ai_actions"
MANAGE_CONVERSATIONS = "manage_conversations"
CONFIGURE_INTEGRATIONS = "configure_integrations"

# Support Engineer — internal staff.
USE_CHAT = "use_chat"
DELETE_OWN_DOCUMENTS = "delete_own_documents"
REINDEX_DOCUMENTS = "reindex_documents"
SEARCH_KNOWLEDGE_BASE = "search_knowledge_base"
CREATE_TICKETS = "create_tickets"
SEARCH_INTERNAL_LOGS = "search_internal_logs"
SEARCH_ORDERS = "search_orders"
SEARCH_PAYMENTS = "search_payments"
USE_AI_AGENT = "use_ai_agent"
VIEW_SOURCES = "view_sources"
VIEW_CONVERSATION_HISTORY = "view_conversation_history"

# Customer — end-user.
CHAT = "chat"
VIEW_OWN_CONVERSATIONS = "view_own_conversations"
UPLOAD_FILES = "upload_files"
DOWNLOAD_GENERATED_ANSWERS = "download_generated_answers"


# Canonical set of every permission we recognise. ``role_permissions``
# below distributes from this set so a typo in either side becomes a
# ``KeyError`` at import time rather than a silent "no permission"
# check at runtime.
PERMISSIONS: frozenset[str] = frozenset(
    {
        # Platform Admin
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
        # Organization Admin
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
        # Support Engineer
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
        # Customer
        CHAT,
        VIEW_OWN_CONVERSATIONS,
        UPLOAD_FILES,
        DOWNLOAD_GENERATED_ANSWERS,
    }
)


# Role → permission set. Mirrors the product spec exactly.
# Cross-tenant Platform Admin is a strict superset of Organization Admin
# (defence-in-depth: every org-admin operation must work for them).
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "platform_admin": frozenset(
        {
            # Cross-tenant platform-admin superset.
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
            # Inherits every org-admin permission so a freshly-promoted
            # platform_admin can still see/do the admin section without
            # needing parallel role flags.
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
            # And inherits every support-engineer permission.
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
            # And customer (for support surfaces).
            CHAT,
            VIEW_OWN_CONVERSATIONS,
            UPLOAD_FILES,
            DOWNLOAD_GENERATED_ANSWERS,
        }
    ),
    "admin": frozenset(
        {
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
            # Org admins can use chat / search KB / etc. when operating
            # in their own tenant context — same surface as staff.
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
    ),
    "support_engineer": frozenset(
        {
            USE_CHAT,
            UPLOAD_DOCUMENTS,
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
            # Same chat / view-own surface as customers (so the
            # support UI can demo the customer perspective).
            CHAT,
            VIEW_OWN_CONVERSATIONS,
            UPLOAD_FILES,
            DOWNLOAD_GENERATED_ANSWERS,
        }
    ),
    "customer": frozenset(
        {
            CHAT,
            VIEW_OWN_CONVERSATIONS,
            UPLOAD_FILES,
            VIEW_SOURCES,
            DOWNLOAD_GENERATED_ANSWERS,
        }
    ),
}


def permissions_for_role(role: str) -> frozenset[str]:
    """Return the permission set for ``role`` or an empty set on unknown.

    Unknown roles get an empty set rather than raising — the auth
    dependency layer is the authoritative gate, this is just a catalog
    lookup. Returning ``frozenset()`` keeps call sites simple: every
    check is a no-op rather than a 500.
    """
    return ROLE_PERMISSIONS.get(role, frozenset())


def has_permission(role: str, permission: str) -> bool:
    """True iff ``role`` has ``permission`` in its catalog.

    Unknown roles → False. Unknown permissions → False. Both kinds of
    typo-safe defaults keep a future permission string from accidentally
    granting access to every role.
    """
    if permission not in PERMISSIONS:
        return False
    return permission in permissions_for_role(role)

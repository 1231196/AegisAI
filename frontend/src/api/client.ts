/**
 * Typed fetch client for the backend API.
 *
 * Why this exists instead of using ``fetch`` directly:
 *   1. Auto-attaches the Bearer access token.
 *   2. On 401 from any non-auth endpoint, attempts a single-flight
 *      ``/auth/refresh`` exchange and retries the original request once.
 *      Concurrent requests during a refresh share one in-flight promise.
 *   3. ``ApiError`` carries the status + detail so callers can map to UX.
 *
 * The client is a plain singleton (not a Context) — auth state is owned by
 * AuthContext, which feeds tokens in via ``setTokens``.
 */

const API_BASE = "/api";

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  username: string;
  role: string;
  disabled: boolean;
  organization_id: string;
}

// Canonical role set; keep in sync with backend `app.auth.schemas.ROLES`
// (frozenset({"platform_admin", "admin", "support_engineer", "customer"})).
// Mirroring here avoids a chatty round-trip just to populate the role <select>.
// The ``Role`` type is the *user-assignable* set (no ``platform_admin`` —
// promoting someone to platform-admin is an out-of-band operator action,
// not a UI workflow).
export const ROLES = ["admin", "support_engineer", "customer"] as const;
export type Role = (typeof ROLES)[number];

/**
 * Admin role sentinel. Centralised so Sidebar and App's "show users"
 * gate share one source of truth. Mirrors the canonical string in
 * ROLES — exporting explicitly so renames cross-reference cleanly.
 */
export const ADMIN_ROLE = "admin" as const;
export const isAdmin = (role: string | undefined | null): boolean =>
  role === ADMIN_ROLE;

/**
 * Platform-admin sentinel. Cross-tenant operator scope: can manage
 * every organisation and every user across organisations. Backend
 * mirrors this via ``app.auth.schemas.CROSS_TENANT_ROLES``.
 *
 * ``platform_admin`` is a strict superset of ``admin`` — every admin
 * permission plus cross-tenant access — so even though no UI workflow
 * currently promotes someone to it directly, a freshly-promoted
 * platform_admin must still see the full admin section in the sidebar
 * (otherwise the operator lands on the dashboard with no menu items).
 */
export const PLATFORM_ADMIN_ROLE = "platform_admin" as const;
export const isPlatformAdmin = (
  role: string | undefined | null,
): boolean => role === PLATFORM_ADMIN_ROLE;

/**
 * Customer role sentinel. Customer accounts get a completely different
 * landing surface ("Customer Portal" — chat + own conversations) and
 * a sidebar with NO staff navigation items.
 */
export const CUSTOMER_ROLE = "customer" as const;
export const isCustomer = (
  role: string | undefined | null,
): boolean => role === CUSTOMER_ROLE;

/**
 * Support-engineer role sentinel. ``support_engineer`` is the main
 * internal user — has the full staff nav and AI-agent surfaces but
 * NO admin / org-management items.
 */
export const SUPPORT_ENGINEER_ROLE = "support_engineer" as const;
export const isSupportEngineer = (
  role: string | undefined | null,
): boolean => role === SUPPORT_ENGINEER_ROLE;

/**
 * Permission catalog mirror. Mirror of the backend
 * ``app.auth.permissions.PERMISSIONS`` set, exposed here so the front
 * end does not have to hardcode the strings in two places. Span the
 * four product-spec role tiers verbatim.
 *
 * A new permission added to the backend without a matching entry here
 * would render as a missing menu item / disabled button — the
 * asymmetry is the intended UI-side nag, NOT something to silently
 * paper over.
 */
export const PERMISSIONS = [
  // Platform Admin (Super Admin)
  "manage_all_organizations",
  "manage_all_users",
  "configure_global_ai_settings",
  "configure_available_llms",
  "configure_mcp_servers",
  "view_global_analytics",
  "view_all_logs",
  "manage_billing",
  "access_monitoring",
  "access_evaluation_dashboards",
  // Organization Admin
  "manage_users",
  "upload_documents",
  "delete_org_documents",
  "manage_knowledge_base",
  "configure_org_ai_settings",
  "view_org_analytics",
  "view_org_logs",
  "approve_ai_actions",
  "manage_conversations",
  "configure_integrations",
  // Support Engineer
  "use_chat",
  "delete_own_documents",
  "reindex_documents",
  "search_knowledge_base",
  "create_tickets",
  "search_internal_logs",
  "search_orders",
  "search_payments",
  "use_ai_agent",
  "view_sources",
  "view_conversation_history",
  // Customer
  "chat",
  "view_own_conversations",
  "upload_files",
  "download_generated_answers",
] as const;
export type Permission = (typeof PERMISSIONS)[number];

/**
 * Permission look-up mirror. Same data as the backend
 * ``app.auth.permissions.ROLE_PERMISSIONS`` dict, mirrored here so
 * the SPA can render role-aware UI before the network confirms it.
 * The network call (``GET /auth/me/permissions``) is the source of
 * truth; this is the optimistic default.
 */
export const ROLE_PERMISSIONS: Record<string, readonly Permission[]> = {
  platform_admin: [
    // Cross-tenant superset
    "manage_all_organizations",
    "manage_all_users",
    "configure_global_ai_settings",
    "configure_available_llms",
    "configure_mcp_servers",
    "view_global_analytics",
    "view_all_logs",
    "manage_billing",
    "access_monitoring",
    "access_evaluation_dashboards",
    // Org-admin inheritance
    "manage_users",
    "upload_documents",
    "delete_org_documents",
    "manage_knowledge_base",
    "configure_org_ai_settings",
    "view_org_analytics",
    "view_org_logs",
    "approve_ai_actions",
    "manage_conversations",
    "configure_integrations",
    // Support-engineer inheritance
    "use_chat",
    "delete_own_documents",
    "reindex_documents",
    "search_knowledge_base",
    "create_tickets",
    "search_internal_logs",
    "search_orders",
    "search_payments",
    "use_ai_agent",
    "view_sources",
    "view_conversation_history",
    // Customer inheritance (so support surfaces still work)
    "chat",
    "view_own_conversations",
    "upload_files",
    "download_generated_answers",
  ],
  admin: [
    "manage_users",
    "upload_documents",
    "delete_org_documents",
    "manage_knowledge_base",
    "configure_org_ai_settings",
    "view_org_analytics",
    "view_org_logs",
    "approve_ai_actions",
    "manage_conversations",
    "configure_integrations",
    "use_chat",
    "delete_own_documents",
    "reindex_documents",
    "search_knowledge_base",
    "create_tickets",
    "search_internal_logs",
    "search_orders",
    "search_payments",
    "use_ai_agent",
    "view_sources",
    "view_conversation_history",
    "chat",
    "view_own_conversations",
    "upload_files",
    "download_generated_answers",
  ],
  support_engineer: [
    "use_chat",
    "upload_documents",
    "delete_own_documents",
    "reindex_documents",
    "search_knowledge_base",
    "create_tickets",
    "search_internal_logs",
    "search_orders",
    "search_payments",
    "use_ai_agent",
    "view_sources",
    "view_conversation_history",
    "chat",
    "view_own_conversations",
    "upload_files",
    "download_generated_answers",
  ],
  customer: [
    "chat",
    "view_own_conversations",
    "upload_files",
    "view_sources",
    "download_generated_answers",
  ],
};

/**
 * Permissions granted to ``role`` from the optimistic front-end
 * mirror. Backend ``GET /auth/me/permissions`` is the source of
 * truth at runtime; this function powers the first paint before
 * the network confirms it (avoids a "no menu" flash on slow
 * networks).
 */
export function permissionsForRole(role: string | undefined | null): readonly Permission[] {
  if (!role) return [];
  return ROLE_PERMISSIONS[role] ?? [];
}

/**
 * Permission check. Looks at the optimistic mirror (the ``permissions``
 * array attached to AuthContext by ``fetchPermissions`` is preferred
 * if non-empty — pass it as the 3rd arg). Unknown roles / permissions
 * → false. Typed ``string`` not just ``Permission`` so callers can
 * pass arbitrary catalog values without an initial cast.
 */
export function hasPermission(
  role: string | undefined | null,
  permission: string,
  grantedSet?: readonly string[],
): boolean {
  if (grantedSet && grantedSet.length > 0) {
    return grantedSet.includes(permission);
  }
  return permissionsForRole(role).includes(permission as Permission);
}

export interface CreateUserRequest {
  username: string;
  password: string;
  role: Role;
  organization_id: string;
  disabled?: boolean;
}

/**
 * Body of PATCH /users/{id}. All fields optional: only the dirty ones
 * are sent so we don't trigger useless bcrypt re-hashes when
 * the admin toggles `disabled`.
 *
 * ``organization_id`` is a *transfer* to another organisation. The
 * backend will revoke the user's refresh tokens on transfer so the
 * next /refresh picks up the new org in the access JWT payload.
 */
export interface UpdateUserRequest {
  password?: string;
  role?: Role;
  disabled?: boolean;
  organization_id?: string;
}

export interface OrganizationResponse {
  id: string;
  name: string;
  slug: string;
}

export interface CreateOrganizationRequest {
  name: string;
  slug: string;
}

export interface PermissionsResponse {
  role: string;
  permissions: string[];
}

// Knowledge Base (Epic 3). Mirrors backend-api's DocumentOut schema
// (app/documents/schemas.py) field-for-field.
export const DOCUMENT_STATUSES = ["processing", "indexed", "failed"] as const;
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

// Extensions accepted by POST /documents (US-008). Mirrors
// app/documents/schemas.py's ALLOWED_EXTENSIONS keys.
export const ALLOWED_DOCUMENT_EXTENSIONS = ["pdf", "docx", "txt", "md", "csv"] as const;

export interface DocumentResponse {
  id: string;
  organization_id: string;
  uploaded_by: string;
  filename: string;
  file_type: string;
  size_bytes: number;
  status: DocumentStatus;
  chunk_count: number | null;
  content_hash: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  indexed_at: string | null;
}

// Chat (Epic 5). Mirrors backend-api's ConversationOut/MessageOut
// schemas (app/conversations/schemas.py) field-for-field.
export interface ConversationResponse {
  id: string;
  organization_id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources_json: string | null;
  created_at: string;
}

// Mirrors backend-ai's SourceResult (app/retrieval/schemas.py) — this
// is what's inside a parsed MessageResponse.sources_json.
export interface ChatSourceResult {
  document_id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number;
  text: string;
  excerpt: string;
  score: number;
  rerank_score: number;
}

export type ChatStreamEvent =
  | { event: "sources"; data: { results: ChatSourceResult[] } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: Record<string, never> }
  | { event: "error"; data: { message: string } };

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(`HTTP ${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshInFlight: Promise<string | null> | null = null;

  setTokens(refresh: string | null, access: string | null): void {
    this.refreshToken = refresh;
    this.accessToken = access;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  getRefreshToken(): string | null {
    return this.refreshToken;
  }

  /**
   * Issue a JSON (or, for a ``FormData`` body, multipart) request. If
   * the server returns 401 and we have a refresh token, performs a
   * single attempt at rotation + retry. Refresh-on-401 deliberately
   * disabled for the auth lifecycle endpoints (login / register /
   * refresh itself) to avoid recursion.
   *
   * ``FormData`` bodies (document upload) are passed through as-is
   * with no ``Content-Type`` header set — the browser fills in
   * ``multipart/form-data; boundary=...`` itself, which it can only
   * do correctly if we don't set the header manually.
   */
  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    opts: { allowRefresh?: boolean; retry?: boolean } = {
      allowRefresh: true,
      retry: true,
    },
  ): Promise<T> {
    const isFormData = body instanceof FormData;
    const headers: Record<string, string> = {
      Accept: "application/json",
    };
    if (!isFormData) {
      headers["Content-Type"] = "application/json";
    }
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body:
        body === undefined
          ? undefined
          : body instanceof FormData
            ? body
            : JSON.stringify(body),
      credentials: "omit",
    });

    if (
      res.status === 401 &&
      opts.allowRefresh &&
      opts.retry &&
      this.refreshToken
    ) {
      const newAccess = await this.refreshOnce();
      if (!newAccess) {
        throw new ApiError(401, "Session expired");
      }
      return this.request(method, path, body, { ...opts, retry: false });
    }

    if (!res.ok) {
      let detail = res.statusText;
      try {
        const j = (await res.json()) as { detail?: string };
        detail = j.detail ?? JSON.stringify(j);
      } catch {
        /* keep statusText */
      }
      throw new ApiError(res.status, detail);
    }

    if (res.status === 204) {
      return undefined as T;
    }
    return (await res.json()) as T;
  }

  /**
   * Single-flight refresh. Concurrent callers share one POST /auth/refresh
   * and receive the same new access token. On any failure the refresh
   * token is dropped locally and ``null`` is returned.
   */
  private refreshOnce(): Promise<string | null> {
    if (this.refreshInFlight) return this.refreshInFlight;
    this.refreshInFlight = (async () => {
      const current = this.refreshToken;
      if (!current) return null;
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: current }),
          credentials: "omit",
        });
        if (!res.ok) {
          this.refreshToken = null;
          clearStoredRefresh();
          return null;
        }
        const tokens = (await res.json()) as TokenPairResponse;
        this.accessToken = tokens.access_token;
        this.refreshToken = tokens.refresh_token;
        // Persist the rotated refresh so a tab reload before the next
        // login doesn't try to re-hydrate from the (now revoked) old jti.
        storeRefresh(tokens.refresh_token);
        return tokens.access_token;
      } catch {
        this.refreshToken = null;
        clearStoredRefresh();
        return null;
      } finally {
        this.refreshInFlight = null;
      }
    })();
    return this.refreshInFlight;
  }

  // -- public surface ---------------------------------------------------

  async login(username: string, password: string): Promise<TokenPairResponse> {
    const tokens = await this.request<TokenPairResponse>(
      "POST",
      "/auth/login",
      { username, password },
      { allowRefresh: false, retry: false },
    );
    this.setTokens(tokens.refresh_token, tokens.access_token);
    return tokens;
  }

  async register(
    email: string,
    password: string,
  ): Promise<TokenPairResponse> {
    const tokens = await this.request<TokenPairResponse>(
      "POST",
      "/auth/register",
      { email, password },
      { allowRefresh: false, retry: false },
    );
    this.setTokens(tokens.refresh_token, tokens.access_token);
    return tokens;
  }

  async fetchMe(): Promise<UserResponse> {
    return this.request<UserResponse>("GET", "/auth/me");
  }

  async fetchPermissions(): Promise<PermissionsResponse> {
    return this.request<PermissionsResponse>("GET", "/auth/me/permissions");
  }

  // --- admin: user management ----------------------------------------
  // These re-use the same bearer/refresh-once plumbing as the rest of
  // the client (request() side-effect). 403 from any of them means the
  // caller was demoted mid-session and the page-level handler should
  // bounce them to the dashboard.

  async listUsers(): Promise<UserResponse[]> {
    return this.request<UserResponse[]>("GET", "/users");
  }

  async createUser(payload: CreateUserRequest): Promise<UserResponse> {
    return this.request<UserResponse>("POST", "/users", payload);
  }

  async updateUser(
    id: string,
    patch: UpdateUserRequest,
  ): Promise<UserResponse> {
    return this.request<UserResponse>("PATCH", `/users/${encodeURIComponent(id)}`, patch);
  }

  async deleteUser(id: string): Promise<void> {
    return this.request<void>("DELETE", `/users/${encodeURIComponent(id)}`);
  }

  // --- admin: organisation management (platform-admin only) ---
  // Same bearer + refresh-once plumbing as the rest of the client.
  // The DELETE endpoint is gated to platform_admin in the backend so
  // plain admins will get a 403 which surfaces here as an ApiError.

  async listOrganizations(): Promise<OrganizationResponse[]> {
    return this.request<OrganizationResponse[]>("GET", "/organizations");
  }

  async createOrganization(
    payload: CreateOrganizationRequest,
  ): Promise<OrganizationResponse> {
    return this.request<OrganizationResponse>(
      "POST",
      "/organizations",
      payload,
    );
  }

  async deleteOrganization(id: string): Promise<void> {
    return this.request<void>(
      "DELETE",
      `/organizations/${encodeURIComponent(id)}`,
    );
  }

  // --- Knowledge Base documents (Epic 3) ---
  // Same bearer + refresh-once plumbing as the rest of the client.
  // Upload returns immediately with status "processing" — the actual
  // parse/chunk/embed pipeline runs asynchronously in backend-ai, so
  // callers poll listDocuments()/getDocument() for the terminal state.

  async listDocuments(): Promise<DocumentResponse[]> {
    return this.request<DocumentResponse[]>("GET", "/documents");
  }

  async getDocument(id: string): Promise<DocumentResponse> {
    return this.request<DocumentResponse>("GET", `/documents/${encodeURIComponent(id)}`);
  }

  async uploadDocument(file: File): Promise<DocumentResponse> {
    const form = new FormData();
    form.append("file", file);
    return this.request<DocumentResponse>("POST", "/documents", form);
  }

  async reindexDocument(id: string): Promise<DocumentResponse> {
    return this.request<DocumentResponse>(
      "POST",
      `/documents/${encodeURIComponent(id)}/reindex`,
    );
  }

  async deleteDocument(id: string): Promise<void> {
    return this.request<void>("DELETE", `/documents/${encodeURIComponent(id)}`);
  }

  // --- Chat (Epic 5) ---
  // Same bearer + refresh-once plumbing as the rest of the client for
  // the plain CRUD calls. sendMessage() is different — see below.

  async listConversations(): Promise<ConversationResponse[]> {
    return this.request<ConversationResponse[]>("GET", "/conversations");
  }

  async createConversation(): Promise<ConversationResponse> {
    return this.request<ConversationResponse>("POST", "/conversations");
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request<void>("DELETE", `/conversations/${encodeURIComponent(id)}`);
  }

  async listMessages(conversationId: string): Promise<MessageResponse[]> {
    return this.request<MessageResponse[]>(
      "GET",
      `/conversations/${encodeURIComponent(conversationId)}/messages`,
    );
  }

  /**
   * Send a message and stream the assistant's reply as it's
   * generated (US-021). Doesn't go through ``request()`` — that
   * method always awaits a full JSON body, but this needs the raw
   * streaming ``Response.body`` to read Server-Sent Events as they
   * arrive.
   *
   * Parses the SSE framing itself (line-by-line, tracking the
   * current ``event:`` until the next blank line) rather than
   * assuming chunk boundaries line up with message boundaries —
   * same approach backend-api's own SSE consumer
   * (``app/documents/ai_client.py``) uses for the upstream hop.
   */
  async *sendMessage(
    conversationId: string,
    content: string,
  ): AsyncGenerator<ChatStreamEvent> {
    const path = `/conversations/${encodeURIComponent(conversationId)}/messages`;
    const doRequest = (): Promise<Response> => {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      };
      if (this.accessToken) {
        headers["Authorization"] = `Bearer ${this.accessToken}`;
      }
      return fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ content }),
        credentials: "omit",
      });
    };

    let res = await doRequest();
    if (res.status === 401 && this.refreshToken) {
      const newAccess = await this.refreshOnce();
      if (newAccess) {
        res = await doRequest();
      }
    }
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const j = (await res.json()) as { detail?: string };
        detail = j.detail ?? JSON.stringify(j);
      } catch {
        /* keep statusText */
      }
      throw new ApiError(res.status, detail);
    }
    if (!res.body) {
      throw new ApiError(0, "Streaming response had no body");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentEvent: string | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let newlineIndex: number;
      while ((newlineIndex = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, newlineIndex).replace(/\r$/, "");
        buffer = buffer.slice(newlineIndex + 1);

        if (line === "") {
          currentEvent = null;
          continue;
        }
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:") && currentEvent) {
          const raw = line.slice(5).trim();
          try {
            yield { event: currentEvent, data: JSON.parse(raw) } as ChatStreamEvent;
          } catch {
            /* malformed frame — skip rather than crash the stream */
          }
        }
      }
    }
  }

  async logout(): Promise<void> {
    // Optimistic local cleanup BEFORE the network round-trip. While
    // the POST /auth/logout is in flight, the singleton's
    // ``this.refreshToken`` would otherwise remain populated, so
    // any concurrent refresh-on-401 (e.g. an authenticated fetch
    // whose access token happened to expire inside the logout
    // window) would race with /auth/logout on the server. That
    // race produces a 401 in the browser console — ``/auth/refresh``
    // returns 401 because the refresh was just revoked by
    // /auth/logout, then ``refreshOnce`` clears ``this.refreshToken``
    // and emits the surfaced ``Failed to load resource`` line the
    // user was reporting on logout+login.
    //
    // Clearing first short-circuits refresh-on-401 (gated on
    // ``this.refreshToken``) before any /auth/refresh can fire.
    const refreshToRevoke = this.refreshToken;
    const accessToRevoke = this.accessToken;
    this.setTokens(null, null);
    clearStoredRefresh();
    if (!refreshToRevoke) return;

    // Bypass ``this.request`` so:
    //   1. The Bearer header is built from the *captured* access
    //      token — ``/auth/logout``'s ``Depends(get_bearer_token)``
    //      requires a header even though the share-state is now
    //      empty. (Also covers the boot-time window where
    //      ``this.accessToken`` is null but ``this.refreshToken``
    //      is set — the access might be in flight inside
    //      ``refreshOnce``, so a stale ``logout`` call used to
    //      401 on missing Bearer.)
    //   2. The 401-interceptor plumbing cannot fire against a
    //      freshly-cleared singleton mid-round-trip.
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        Accept: "application/json",
      };
      if (accessToRevoke) {
        headers["Authorization"] = `Bearer ${accessToRevoke}`;
      }
      await fetch(`${API_BASE}/auth/logout`, {
        method: "POST",
        headers,
        body: JSON.stringify({ refresh_token: refreshToRevoke }),
        credentials: "omit",
      });
    } catch {
      // Local logout already succeeded optimistically. Server
      // revocation is best-effort; the server-side row remains
      // valid until natural expiry if we couldn't reach the server.
    }
  }
}

export const apiClient = new ApiClient();
const REFRESH_STORAGE_KEY = "aegis.refresh";

export function loadStoredRefresh(): string | null {
  try {
    return localStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeRefresh(token: string): void {
  try {
    localStorage.setItem(REFRESH_STORAGE_KEY, token);
  } catch {
    /* private mode — silent */
  }
}

export function clearStoredRefresh(): void {
  try {
    localStorage.removeItem(REFRESH_STORAGE_KEY);
  } catch {
    /* no-op */
  }
}

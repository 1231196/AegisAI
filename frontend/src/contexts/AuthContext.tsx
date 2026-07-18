import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  ApiError,
  apiClient,
  clearStoredRefresh,
  isCustomer,
  loadStoredRefresh,
  permissionsForRole,
  storeRefresh,
  type UserResponse,
} from "../api/client";

/**
 * Closed union of all "screens" the auth state-machine can route to.
 *
 * Exported so low-level UI components (Sidebar / AppShell / future
 * nav bars) can type their ``onNavigate`` callback against the same
 * source of truth the context uses, without re-declaring the
 * allowed values.
 *
 * ``"chat"`` is the customer-only landing screen; staff users never
 * see it. ``"dashboard"`` is the staff landing.
 */
export type Screen =
  | "login"
  | "register"
  | "verify"
  | "dashboard"
  | "chat"
  | "users"
  | "organizations"
  | "loading";

interface AuthState {
  user: UserResponse | null;
  /** Permission set derived from the backend catalog. Empty until
   *  ``fetchPermissions`` resolves (or for unauthenticated state).
   *  The Sidebar and per-page role gates should prefer this over
   *  role-string checks when it's non-empty.
   *
   * Typed as ``readonly string[]`` (not ``Permission``) because the
   * server returns arbitrary catalogue strings — the literal union
   * from ``PERMISSIONS`` would over-narrow the assignment and break
   * the API response shape. The optimistic mirror in
   * ``permissionsForRole`` is typed against the literal union, but
   * it is consumed loosely. */
  permissions: readonly string[];
  isLoading: boolean;
  isAuthenticated: boolean;
  pendingVerification: boolean;
  error: string | null;
  screen: Screen;
  registeredEmail: string | null;
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  continueAfterVerify: () => Promise<void>;
  goToLogin: () => void;
  goToRegister: () => void;
  goToScreen: (screen: Screen) => void;
  clearError: () => void;
  // Refresh the local user record so role/disable changes propagate
  // without forcing a full logout. Throws on 401/403 so the caller
  // can decide between bounce-dashboard and force-logout paths.
  refreshMe: () => Promise<void>;
}

type AuthContextValue = AuthState & AuthActions;

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    permissions: [],
    isLoading: true,
    isAuthenticated: false,
    pendingVerification: false,
    error: null,
    screen: "loading",
    registeredEmail: null,
  });

  // On mount: try to re-hydrate from the localStorage-stored refresh
  // token by exchanging it for a fresh access token + user record.
  //
  // Both ``/auth/me`` and ``/auth/me/permissions`` are required: the
  // first for the user record, the second for the permission set that
  // drives role-aware UI. We fire them in parallel for speed and
  // tolerate a permissions failure (a 5xx response falls back to an
  // empty set rather than blocking the whole hydrate).
  useEffect(() => {
    let cancelled = false;
    const stored = loadStoredRefresh();
    if (!stored) {
      setState((s) => ({
        ...s,
        isLoading: false,
        screen: "login",
      }));
      return;
    }
    apiClient.setTokens(stored, null);
    Promise.all([
      apiClient.fetchMe().catch(() => null),
      apiClient.fetchPermissions().catch(() => null),
    ])
      .then(([user, perms]) => {
        if (cancelled) return;
        if (user === null) {
          // ``fetchMe`` failed (401/403/etc.) — the previous fix
          // path: clear local state and route to login.
          clearStoredRefresh();
          apiClient.setTokens(null, null);
          setState((s) => ({
            ...s,
            isLoading: false,
            screen: "login",
          }));
          return;
        }
        const permissions = perms?.permissions ?? [];
        setState({
          user,
          permissions,
          isLoading: false,
          isAuthenticated: true,
          pendingVerification: false,
          error: null,
          // Customer lands on the chat portal; everyone else on the
          // staff dashboard. The optimistic front-end mirror
          // (``isCustomer``) reads the role string directly so a slow
          // /me/permissions response doesn't strand them on the
          // wrong landing for the first paint.
          screen: isCustomer(user.role) ? "chat" : "dashboard",
          registeredEmail: null,
        });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, error: null, isLoading: false, screen: s.screen }));
    try {
      const tokens = await apiClient.login(email, password);
      storeRefresh(tokens.refresh_token);
      // Fetch user + permissions in parallel; permissions failure is
      // tolerated (falls back to optimistic ROLE_PERMISSIONS mirror).
      const [user, perms] = await Promise.all([
        apiClient.fetchMe(),
        apiClient.fetchPermissions().catch(() => null),
      ]);
      const permissions = perms?.permissions ?? [];
      setState({
        user,
        permissions,
        isLoading: false,
        isAuthenticated: true,
        pendingVerification: false,
        error: null,
        // Customer → chat portal, staff → dashboard.
        screen: isCustomer(user.role) ? "chat" : "dashboard",
        registeredEmail: null,
      });
    } catch (err) {
      setState((s) => ({
        ...s,
        isLoading: false,
        error: errorMessage(err, "Unable to sign in. Please try again."),
      }));
      throw err;
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    setState((s) => ({ ...s, error: null }));
    try {
      const tokens = await apiClient.register(email, password);
      storeRefresh(tokens.refresh_token);
      setState((s) => ({
        ...s,
        isAuthenticated: true,
        pendingVerification: true,
        screen: "verify",
        registeredEmail: email,
        error: null,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        error: errorMessage(
          err,
          "Unable to create an account. Please try again.",
        ),
      }));
      throw err;
    }
  }, []);

  const continueAfterVerify = useCallback(async () => {
    // Clear any stale error pill before retrying so the user gets a
    // honest loading signal rather than a lingering message.
    setState((s) => ({ ...s, error: null }));
    try {
      const [user, perms] = await Promise.all([
        apiClient.fetchMe(),
        apiClient.fetchPermissions().catch(() => null),
      ]);
      setState((s) => ({
        ...s,
        user,
        permissions: perms?.permissions ?? [],
        pendingVerification: false,
        screen: isCustomer(user.role) ? "chat" : "dashboard",
        error: null,
      }));
    } catch (err) {
      // /auth/me failed mid-transition — never strand the user on the
      // verify screen. Drop them back to login with a friendly error so
      // they can re-authenticate.
      await apiClient.logout().catch(() => undefined);
      setState({
        user: null,
        permissions: [],
        isLoading: false,
        isAuthenticated: false,
        pendingVerification: false,
        error: errorMessage(err, "Could not load your account."),
        screen: "login",
        registeredEmail: null,
      });
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    await apiClient.logout();
    clearStoredRefresh();
    setState({
      user: null,
      permissions: [],
      isLoading: false,
      isAuthenticated: false,
      pendingVerification: false,
      error: null,
      screen: "login",
      registeredEmail: null,
    });
  }, []);

  const goToLogin = useCallback(() => {
    setState((s) => ({ ...s, screen: "login", error: null }));
  }, []);
  const goToRegister = useCallback(() => {
    setState((s) => ({ ...s, screen: "register", error: null }));
  }, []);
  // Generic screen-setter used by the authenticated sidebar router.
  // TypeScript enforces the closed union, so no runtime coercion
  // needed past what the type guarantees.
  const goToScreen = useCallback((next: Screen) => {
    setState((s) => ({ ...s, screen: next, error: null }));
  }, []);
  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  /**
   * Re-pull the current user. On API auth failure (401/403), clear
   * the local session so stale role/disable state cannot drive
   * page-level rendering after the server has revoked the user.
   * Page-level catchers handle the user-facing flow.
   *
   * Also refreshes the permission set so a role change (e.g. an
   * out-of-band promotion) propagates without forcing a full
   * logout. If ``/auth/me`` succeeds but ``/auth/me/permissions``
   * fails, we keep the previous permissions rather than wiping them.
   */
  const refreshMe = useCallback(async () => {
    try {
      const [user, perms] = await Promise.all([
        apiClient.fetchMe(),
        apiClient.fetchPermissions().catch(() => null),
      ]);
      setState((s) => ({
        ...s,
        user,
        // Fall through to the optimistic mirror derived from the
        // *current* (refreshed) role when the permissions fetch
        // fails — never reuse the cached ``s.permissions`` because
        // a stale set paired with a new role leaks menu items the
        // user is no longer entitled to (e.g. an admin demoted to
        // customer mid-session would still see the Admin section).
        permissions: perms?.permissions ?? permissionsForRole(user.role),
      }));
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        // Stale token or server-side revoke — wipe local session.
        clearStoredRefresh();
        apiClient.setTokens(null, null);
        setState({
          user: null,
          permissions: [],
          isLoading: false,
          isAuthenticated: false,
          pendingVerification: false,
          error: null,
          screen: "login",
          registeredEmail: null,
        });
        return;
      }
      // Network / 5xx — leave state alone; caller decides UI.
      throw err;
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      login,
      register,
      logout,
      continueAfterVerify,
      goToLogin,
      goToRegister,
      goToScreen,
      clearError,
      refreshMe,
    }),
    [
      state,
      login,
      register,
      logout,
      continueAfterVerify,
      goToLogin,
      goToRegister,
      goToScreen,
      clearError,
      refreshMe,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an <AuthProvider>");
  }
  return ctx;
}

function errorMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    // Translate canonical backend errors into human-friendly strings.
    if (err.status === 401) return "Invalid email or password";
    if (err.status === 409) return "An account with that email already exists";
    if (err.status === 422) return "Please check your input and try again";
    return err.detail || fallback;
  }
  if (err instanceof Error) return err.message || fallback;
  return fallback;
}

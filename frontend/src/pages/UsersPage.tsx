import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { PasswordInput } from "../components/PasswordInput";
import {
  ApiError,
  apiClient,
  type OrganizationResponse,
  isPlatformAdmin,
  type Role,
  ROLES,
  type UserResponse,
} from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import "./UsersPage.css";

interface UsersPageProps {
  user: UserResponse;
  onRevoked: () => void;
}

interface NewUserDraft {
  email: string;
  password: string;
  role: Role;
  organization_id: string;
  disabled: boolean;
}

const EMPTY_DRAFT: NewUserDraft = {
  email: "",
  password: "",
  role: "customer",
  organization_id: "", // filled on openCreate from caller-then-list
  disabled: false,
};

function emailIsValid(value: string): boolean {
  // Mirrors backend's relaxed RFC check in app/auth/schemas.py
  // (just an "@", no whitespace, non-empty) so we don't send garbage
  // assets into a wasted network round-trip.
  return value.includes("@") && !/\s/.test(value) && value.length >= 3;
}

export function UsersPage({ user, onRevoked }: UsersPageProps) {
  const auth = useAuth();
  const callerIsPlatformAdmin = isPlatformAdmin(user.role);
  const [users, setUsers] = useState<UserResponse[] | null>(null);
  const [orgs, setOrgs] = useState<OrganizationResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rowBusy, setRowBusy] = useState<Record<string, boolean>>({});
  const [showCreate, setShowCreate] = useState(false);
  const [draft, setDraft] = useState<NewUserDraft>({
    ...EMPTY_DRAFT,
    organization_id: user.organization_id,
  });
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);


  /**
   * Map an ApiError into the right user-facing reaction. 403 means the
   * admin was revoked server-side mid-session; 401 means the access
   * token expired and the refresh-once recovery failed (so the user
   * must sign in again); anything else is a recoverable server error
   * with a detail message to render.
   */
  const handleApiError = useCallback(
    (err: unknown, fallback: string): string | null => {
      if (err instanceof ApiError && err.status === 403) {
        // Admin revoked. Refresh first so the role downgrade is
        // reflected in auth state, then bounce.
        void auth.refreshMe().finally(onRevoked);
        return null;
      }
      if (err instanceof ApiError && err.status === 401) {
        // Stale session; refreshMe clears user and resets screen to
        // 'login' on its own. The component unmounts via parent.
        void auth.refreshMe();
        return null;
      }
      return err instanceof ApiError ? err.detail : fallback;
    },
    [auth, onRevoked],
  );

  const refreshUsers = useCallback(async () => {
    try {
      const list = await apiClient.listUsers();
      setUsers(list);
      setLoadError(null);
    } catch (err) {
      const msg = handleApiError(err, "Unable to load users.");
      if (msg) setLoadError(msg);
    }
  }, [handleApiError]);

  const refreshOrgs = useCallback(async () => {
    // Only platform_admin gets the cross-tenant org list; we still ask
    // so a logged-in admin who is later promoted can populate without
    // a full reload cycle.
    try {
      const list = await apiClient.listOrganizations();
      setOrgs(list);
    } catch (err) {
      // Non-fatal: the org dropdown falls back to caller's own id
      // when this fails so the table still renders. We log so a
      // platform_admin who lands on the page with an empty org
      // dropdown can self-diagnose from the devtools console.
      // 403 (non-platform-admin) is expected — suppress only that.
      if (err instanceof ApiError && err.status !== 403) {
        // eslint-disable-next-line no-console
        console.warn("UsersPage: failed to list organisations", err);
      }
    }
  }, []);

  useEffect(() => {
    void refreshUsers();
    void refreshOrgs();
  }, [refreshUsers, refreshOrgs]);

  const toggleDisabled = useCallback(
    async (target: UserResponse) => {
      setRowBusy((m) => ({ ...m, [target.id]: true }));
      try {
        await apiClient.updateUser(target.id, { disabled: !target.disabled });
        await refreshUsers();
      } catch (err) {
        const msg = handleApiError(err, "Unable to update user.");
        if (msg) setLoadError(msg);
      } finally {
        setRowBusy((m) => ({ ...m, [target.id]: false }));
      }
    },
    [refreshUsers, handleApiError],
  );

  const changeRole = useCallback(
    async (target: UserResponse, role: Role) => {
      if (role === target.role) return;
      setRowBusy((m) => ({ ...m, [target.id]: true }));
      try {
        await apiClient.updateUser(target.id, { role });
        await refreshUsers();
      } catch (err) {
        const msg = handleApiError(err, "Unable to update user role.");
        if (msg) setLoadError(msg);
      } finally {
        setRowBusy((m) => ({ ...m, [target.id]: false }));
      }
    },
    [refreshUsers, handleApiError],
  );

  const changeOrg = useCallback(
    async (target: UserResponse, newOrgId: string) => {
      // No-op if the caller picked the user's existing org.
      if (newOrgId === target.organization_id) return;
      if (!callerIsPlatformAdmin) {
        setLoadError(
          "Only platform admins can move users between organisations.",
        );
        return;
      }
      setRowBusy((m) => ({ ...m, [target.id]: true }));
      try {
        await apiClient.updateUser(target.id, { organization_id: newOrgId });
        await refreshUsers();
      } catch (err) {
        const msg = handleApiError(err, "Unable to transfer user.");
        if (msg) setLoadError(msg);
      } finally {
        setRowBusy((m) => ({ ...m, [target.id]: false }));
      }
    },
    [refreshUsers, handleApiError, callerIsPlatformAdmin],
  );

  const deleteUser = useCallback(
    async (target: UserResponse) => {
      // Self-delete guard; matches backend's "Cannot delete yourself"
      // defence-in-depth so the user doesn't even see a confusing
      // 400 from the server.
      if (target.id === user.id) {
        setLoadError("You cannot delete your own account.");
        return;
      }
      // High-intent, low-frequency action — native confirm() is the
      // smallest UI surface that still gives a hard stop.
      const ok = window.confirm(
        `Delete ${target.username}? This cannot be undone.`,
      );
      if (!ok) return;
      setRowBusy((m) => ({ ...m, [target.id]: true }));
      try {
        await apiClient.deleteUser(target.id);
        await refreshUsers();
      } catch (err) {
        const msg = handleApiError(err, "Unable to delete user.");
        if (msg) setLoadError(msg);
      } finally {
        setRowBusy((m) => ({ ...m, [target.id]: false }));
      }
    },
    [refreshUsers, handleApiError, user.id],
  );

  const openCreate = useCallback(() => {
    setDraft({ ...EMPTY_DRAFT, organization_id: user.organization_id });
    setCreateError(null);
    setShowCreate(true);
  }, [user.organization_id]);

  const submitCreate = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!emailIsValid(draft.email)) {
        setCreateError("Please enter a valid email address.");
        return;
      }
      if (draft.password.length < 8) {
        setCreateError("Password must be at least 8 characters.");
        return;
      }
      if (!callerIsPlatformAdmin && draft.organization_id !== user.organization_id) {
        setCreateError(
          "You can only create users in your own organisation.",
        );
        return;
      }
      setCreating(true);
      try {
        await apiClient.createUser({
          username: draft.email.trim().toLowerCase(),
          password: draft.password,
          role: draft.role,
          organization_id: draft.organization_id,
          disabled: draft.disabled,
        });
        setShowCreate(false);
        await refreshUsers();
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setCreateError("A user with that email already exists.");
          return;
        }
        const msg = handleApiError(err, "Unable to create user.");
        if (msg) setCreateError(msg);
      } finally {
        setCreating(false);
      }
    },
    [draft, user.organization_id, refreshUsers, handleApiError, callerIsPlatformAdmin],
  );

  // Modal keyboard handler: Escape closes when not mid-submit.
  // Outside-click already handles the mouse path.
  useEffect(() => {
    if (!showCreate) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !creating) setShowCreate(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showCreate, creating]);

  const draftPasswordInvalid = useMemo(
    () => draft.password.length > 0 && draft.password.length < 8,
    [draft.password],
  );

  // For non-platform-admin callers, lock the create-modal org picker
  // to the caller's own org. Improves usability AND catches UI bugs
  // before they reach the (already-defended) backend.
  const draftOrgLocked = !callerIsPlatformAdmin;

  return (
    <div className="aegis-users">
      <div className="aegis-users__hero">
        <div>
          <h1 className="aegis-users__title">User management</h1>
          <p className="aegis-users__subtitle">
            {callerIsPlatformAdmin
              ? "Manage members across every organisation in your platform."
              : "Manage members of your organisation. Changes take effect immediately."}
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={openCreate}
          disabled={users === null}
        >
          + New user
        </Button>
      </div>

      {loadError && (
        <div className="aegis-users__banner aegis-users__banner--error" role="alert">
          {loadError}
          <button
            type="button"
            className="aegis-users__banner-dismiss"
            onClick={() => setLoadError(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="aegis-users__panel">
        {users === null && !loadError && (
          <div className="aegis-users__state">Loading users…</div>
        )}
        {users !== null && users.length === 0 && (
          <div className="aegis-users__state">
            No users yet. Click <strong>+ New user</strong> to invite the
            first one.
          </div>
        )}
        {users !== null && users.length > 0 && (
          <table className="aegis-users__table">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                {callerIsPlatformAdmin && <th>Organisation</th>}
                <th>Status</th>
                <th className="aegis-users__table-actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const busy = !!rowBusy[u.id];
                const isSelf = u.id === user.id;
                return (
                  <tr key={u.id} aria-busy={busy || undefined}>
                    <td className="aegis-users__cell-user">
                      <div className="aegis-users__cell-user-row">
                        <span className="aegis-users__cell-username">
                          {u.username}
                        </span>
                        {isSelf && (
                          <span className="aegis-users__you-chip">you</span>
                        )}
                      </div>
                      <span className="aegis-users__cell-id">
                        {u.id.slice(0, 8)}
                      </span>
                    </td>
                    <td>
                      <select
                        className="aegis-users__select"
                        value={u.role}
                        onChange={(e) =>
                          void changeRole(u, e.target.value as Role)
                        }
                        disabled={busy}
                        aria-label={`Change role for ${u.username}`}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>
                            {prettifyRole(r)}
                          </option>
                        ))}
                      </select>
                    </td>
                    {callerIsPlatformAdmin && (
                      <td>
                        <select
                          className="aegis-users__select"
                          value={u.organization_id}
                          onChange={(e) =>
                            void changeOrg(u, e.target.value)
                          }
                          disabled={busy || (orgs ?? []).length === 0}
                          aria-label={`Transfer ${u.username} to another organisation`}
                        >
                          {(orgs ?? []).map((o) => (
                            <option key={o.id} value={o.id}>
                              {o.name} ({o.slug})
                            </option>
                          ))}
                        </select>
                      </td>
                    )}
                    <td>
                      <button
                        type="button"
                        role="switch"
                        aria-checked={!u.disabled}
                        aria-label={`${u.disabled ? "Enable" : "Disable"} ${u.username}`}
                        disabled={busy}
                        onClick={() => void toggleDisabled(u)}
                        className={`aegis-users__switch ${
                          !u.disabled
                            ? "aegis-users__switch--on"
                            : "aegis-users__switch--off"
                        }`}
                      >
                        <span className="aegis-users__switch-knob" />
                        <span className="aegis-users__switch-text">
                          {!u.disabled ? "Active" : "Disabled"}
                        </span>
                      </button>
                    </td>
                    <td className="aegis-users__table-actions-col">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={busy || isSelf}
                        onClick={() => void deleteUser(u)}
                        title={isSelf ? "You cannot delete yourself" : undefined}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <div
          className="aegis-users__modal-scrim"
          role="dialog"
          aria-modal="true"
          aria-labelledby="aegis-users__modal-title"
          onClick={(e) => {
            // Click outside the panel closes — but only when we're not
            // mid-submit, so an accidental outside-click can't lose
            // typed data.
            if (e.target === e.currentTarget && !creating) {
              setShowCreate(false);
            }
          }}
        >
          <form
            className="aegis-users__modal"
            onSubmit={(e) => void submitCreate(e)}
          >
            <h2 id="aegis-users__modal-title" className="aegis-users__modal-title">
              New user
            </h2>
            <p className="aegis-users__modal-sub">
              {callerIsPlatformAdmin
                ? "Choose the organisation this user will belong to."
                : "Will be scoped to your organisation."}
            </p>

            <div className="aegis-users__modal-fields">
              <Input
                type="email"
                label="Email"
                placeholder="user@company.com"
                autoComplete="off"
                required
                value={draft.email}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, email: e.target.value }))
                }
              />
              <PasswordInput
                label="Password"
                placeholder="At least 8 characters"
                autoComplete="new-password"
                required
                value={draft.password}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, password: e.target.value }))
                }
                helperText={
                  draftPasswordInvalid ? "At least 8 characters" : undefined
                }
              />
              <label className="aegis-users__modal-row">
                <span className="aegis-users__modal-row-label">Role</span>
                <select
                  className="aegis-users__select"
                  value={draft.role}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      role: e.target.value as Role,
                    }))
                  }
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {prettifyRole(r)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="aegis-users__modal-row">
                <span className="aegis-users__modal-row-label">
                  Organisation
                </span>
                <select
                  className="aegis-users__select"
                  value={draft.organization_id}
                  disabled={draftOrgLocked || (orgs ?? []).length === 0}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      organization_id: e.target.value,
                    }))
                  }
                  aria-label="Organisation for the new user"
                >
                  {(orgs ?? []).map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name} ({o.slug})
                    </option>
                  ))}
                </select>
                {draftOrgLocked && (
                  <span className="aegis-users__modal-row-hint">
                    You can only create users in your own organisation.
                  </span>
                )}
              </label>
              <label className="aegis-users__modal-row aegis-users__modal-row--inline">
                <input
                  type="checkbox"
                  checked={draft.disabled}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, disabled: e.target.checked }))
                  }
                />
                <span>Create as disabled</span>
              </label>
            </div>

            {createError && (
              <div className="aegis-users__banner aegis-users__banner--error" role="alert">
                {createError}
              </div>
            )}

            <div className="aegis-users__modal-actions">
              <Button
                variant="secondary"
                onClick={() => setShowCreate(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={creating}
                disabled={
                  creating ||
                  !emailIsValid(draft.email) ||
                  draft.password.length < 8 ||
                  draft.organization_id.length === 0
                }
              >
                Create user
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function prettifyRole(role: string): string {
  switch (role) {
    case "admin":
      return "Admin";
    case "support_engineer":
      return "Support engineer";
    case "customer":
      return "Customer";
    default:
      return role;
  }
}

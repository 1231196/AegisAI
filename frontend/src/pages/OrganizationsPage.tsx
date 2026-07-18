import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import {
  ApiError,
  apiClient,
  type OrganizationResponse,
  type UserResponse,
} from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import "./OrganizationsPage.css";

interface OrganizationsPageProps {
  user: UserResponse;
  onRevoked: () => void;
}

interface NewOrgDraft {
  name: string;
  slug: string;
}

const EMPTY_DRAFT: NewOrgDraft = { name: "", slug: "" };

const SLUG_REGEX = /^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$/;

function slugIsValid(value: string): boolean {
  return SLUG_REGEX.test(value.trim().toLowerCase());
}

function prettifySlug(value: string): string {
  // Auto-pretty the slug while the operator types: strip spaces,
  // lowercase, replace internal whitespace with '-', drop leading/
  // trailing dashes. We deliberately do not transform on blur — the
  // operator should see the exact value that will be POSTed.
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function OrganizationsPage({
  user,
  onRevoked,
}: OrganizationsPageProps) {
  const auth = useAuth();
  const [orgs, setOrgs] = useState<OrganizationResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rowBusy, setRowBusy] = useState<Record<string, boolean>>({});
  const [showCreate, setShowCreate] = useState(false);
  const [draft, setDraft] = useState<NewOrgDraft>(EMPTY_DRAFT);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [slugTouched, setSlugTouched] = useState(false);

  // Map an ApiError into the user-facing reaction. Mirror of the
  // UsersPage handler so the two admin pages share semantics.
  const handleApiError = useCallback(
    (err: unknown, fallback: string): string | null => {
      if (err instanceof ApiError && err.status === 403) {
        // platform_admin revoked — fall back to dashboard.
        void auth.refreshMe().finally(onRevoked);
        return null;
      }
      if (err instanceof ApiError && err.status === 401) {
        // Stale session; refreshMe resets to login on its own.
        void auth.refreshMe();
        return null;
      }
      return err instanceof ApiError ? err.detail : fallback;
    },
    [auth, onRevoked],
  );

  const refresh = useCallback(async () => {
    try {
      const list = await apiClient.listOrganizations();
      setOrgs(list);
      setLoadError(null);
    } catch (err) {
      const msg = handleApiError(err, "Unable to load organisations.");
      if (msg) setLoadError(msg);
    }
  }, [handleApiError]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const deleteOrg = useCallback(
    async (target: OrganizationResponse) => {
      // Self-delete guard: refuse to nuke the org your own account
      // belongs to. Operations are recoverable but you should not
      // accidentally strand yourself.
      if (target.id === user.organization_id) {
        setLoadError(
          `Cannot delete the organisation your account is in. Reassign or delete your user first.`,
        );
        return;
      }
      const ok = window.confirm(
        `Delete organisation "${target.name}" (slug: ${target.slug})? This cannot be undone.`,
      );
      if (!ok) return;
      setRowBusy((m) => ({ ...m, [target.id]: true }));
      try {
        await apiClient.deleteOrganization(target.id);
        await refresh();
      } catch (err) {
        const msg = handleApiError(
          err,
          "Unable to delete organisation.",
        );
        if (msg) setLoadError(msg);
      } finally {
        setRowBusy((m) => ({ ...m, [target.id]: false }));
      }
    },
    [refresh, handleApiError, user.organization_id],
  );

  const openCreate = useCallback(() => {
    setDraft(EMPTY_DRAFT);
    setSlugTouched(false);
    setCreateError(null);
    setShowCreate(true);
  }, []);

  const submitCreate = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (draft.name.trim().length === 0) {
        setCreateError("Please enter a name.");
        return;
      }
      if (!slugIsValid(draft.slug)) {
        setCreateError(
          "Slug must be lowercase letters, numbers, or dashes; cannot start or end with a dash.",
        );
        return;
      }
      setCreating(true);
      try {
        await apiClient.createOrganization({
          name: draft.name.trim(),
          slug: draft.slug.trim().toLowerCase(),
        });
        setShowCreate(false);
        await refresh();
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          setCreateError(
            "An organisation with that slug already exists.",
          );
          return;
        }
        const msg = handleApiError(
          err,
          "Unable to create organisation.",
        );
        if (msg) setCreateError(msg);
      } finally {
        setCreating(false);
      }
    },
    [draft, refresh, handleApiError],
  );

  // Escape closes the modal when not mid-submit; outside-click handled
  // inline on the scrim.
  useEffect(() => {
    if (!showCreate) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !creating) setShowCreate(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showCreate, creating]);

  const slugLooksValid = useMemo(
    () => draft.slug.length === 0 || slugIsValid(draft.slug),
    [draft.slug],
  );

  return (
    <div className="aegis-orgs">
      <div className="aegis-orgs__hero">
        <div>
          <h1 className="aegis-orgs__title">Organisations</h1>
          <p className="aegis-orgs__subtitle">
            Manage organisations across the platform. Create new ones
            to onboard new tenants; delete empty ones once members have
            been reassigned.
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={openCreate}
          disabled={orgs === null}
        >
          + New organisation
        </Button>
      </div>

      {loadError && (
        <div
          className="aegis-orgs__banner aegis-orgs__banner--error"
          role="alert"
        >
          {loadError}
          <button
            type="button"
            className="aegis-orgs__banner-dismiss"
            onClick={() => setLoadError(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="aegis-orgs__panel">
        {orgs === null && !loadError && (
          <div className="aegis-orgs__state">Loading organisations…</div>
        )}
        {orgs !== null && orgs.length === 0 && (
          <div className="aegis-orgs__state">
            No organisations yet. Click{" "}
            <strong>+ New organisation</strong> to create the first one.
          </div>
        )}
        {orgs !== null && orgs.length > 0 && (
          <table className="aegis-orgs__table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
                <th className="aegis-orgs__table-actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {orgs.map((o) => {
                const busy = !!rowBusy[o.id];
                const isOwn = o.id === user.organization_id;
                return (
                  <tr key={o.id} aria-busy={busy || undefined}>
                    <td className="aegis-orgs__cell-name">
                      <div className="aegis-orgs__cell-name-row">
                        <span className="aegis-orgs__cell-orgname">
                          {o.name}
                        </span>
                        {isOwn && (
                          <span className="aegis-orgs__you-chip">your org</span>
                        )}
                      </div>
                      <span className="aegis-orgs__cell-id">
                        {o.id.slice(0, 8)}
                      </span>
                    </td>
                    <td>
                      <code className="aegis-orgs__slug-pill">{o.slug}</code>
                    </td>
                    <td className="aegis-orgs__table-actions-col">
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={busy}
                        onClick={() => void deleteOrg(o)}
                        title={
                          isOwn
                            ? "You cannot delete the organisation your account is in"
                            : "Delete this organisation"
                        }
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
          className="aegis-orgs__modal-scrim"
          role="dialog"
          aria-modal="true"
          aria-labelledby="aegis-orgs__modal-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !creating) {
              setShowCreate(false);
            }
          }}
        >
          <form
            className="aegis-orgs__modal"
            onSubmit={(e) => void submitCreate(e)}
          >
            <h2
              id="aegis-orgs__modal-title"
              className="aegis-orgs__modal-title"
            >
              New organisation
            </h2>
            <p className="aegis-orgs__modal-sub">
              New organisations start with zero users. You can add
              members from the User Management screen once the
              organisation exists.
            </p>

            <div className="aegis-orgs__modal-fields">
              <Input
                label="Name"
                placeholder="Acme Corp"
                autoComplete="off"
                required
                value={draft.name}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, name: e.target.value }))
                }
              />
              <Input
                label="Slug"
                placeholder="acme-corp"
                autoComplete="off"
                required
                value={draft.slug}
                helperText={
                  slugTouched && !slugLooksValid
                    ? "Lowercase letters, numbers, and dashes only; cannot start or end with a dash."
                    : "Used in URLs and API identifiers. Lowercase, no spaces."
                }
                onChange={(e) => {
                  const next = prettifySlug(e.target.value);
                  setSlugTouched(true);
                  setDraft((d) => ({ ...d, slug: next }));
                }}
              />
            </div>

            {createError && (
              <div
                className="aegis-orgs__banner aegis-orgs__banner--error"
                role="alert"
              >
                {createError}
              </div>
            )}

            <div className="aegis-orgs__modal-actions">
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
                  draft.name.trim().length === 0 ||
                  !slugIsValid(draft.slug)
                }
              >
                Create organisation
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

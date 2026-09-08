import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { CloseIcon, SearchIcon, UploadIcon } from "../components/icons";
import {
  ALLOWED_DOCUMENT_EXTENSIONS,
  ApiError,
  apiClient,
  hasPermission,
  type DocumentResponse,
  type DocumentStatus,
  type UserResponse,
} from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import "./KnowledgeBasePage.css";

interface KnowledgeBasePageProps {
  user: UserResponse;
  grantedPermissions: readonly string[];
}

type KbTab = "Documents" | "Collections" | "Websites";
const TABS: KbTab[] = ["Documents", "Collections", "Websites"];

type DrawerTab = "Overview" | "Chunks" | "Preview" | "Metadata" | "Activity";
const DRAWER_TABS: DrawerTab[] = ["Overview", "Chunks", "Preview", "Metadata", "Activity"];

const ACCEPT_ATTR = ALLOWED_DOCUMENT_EXTENSIONS.map((ext) => `.${ext}`).join(",");

function statusBadgeClass(status: DocumentStatus) {
  if (status === "indexed") return "aegis-badge--success";
  if (status === "failed") return "aegis-badge--error";
  return "aegis-badge--warning";
}

function statusLabel(status: DocumentStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(1)} ${units[unitIndex]}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export function KnowledgeBasePage({ user, grantedPermissions }: KnowledgeBasePageProps) {
  const auth = useAuth();
  const [tab, setTab] = useState<KbTab>("Documents");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [documents, setDocuments] = useState<DocumentResponse[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rowBusy, setRowBusy] = useState<Record<string, boolean>>({});
  const [uploading, setUploading] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState<DocumentResponse | null>(null);
  const [drawerTab, setDrawerTab] = useState<DrawerTab>("Overview");
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const canUpload = hasPermission(user.role, "upload_documents", grantedPermissions);
  const canDeleteAny = hasPermission(user.role, "delete_org_documents", grantedPermissions);
  const canDeleteOwn = hasPermission(user.role, "delete_own_documents", grantedPermissions);
  const canReindex = hasPermission(user.role, "reindex_documents", grantedPermissions);

  const handleApiError = useCallback(
    (err: unknown, fallback: string): string | null => {
      if (err instanceof ApiError && err.status === 401) {
        // Stale session; refreshMe clears user and resets screen to
        // 'login' on its own.
        void auth.refreshMe();
        return null;
      }
      return err instanceof ApiError ? err.detail : fallback;
    },
    [auth],
  );

  const refreshDocuments = useCallback(async () => {
    try {
      const list = await apiClient.listDocuments();
      setDocuments(list);
      setLoadError(null);
    } catch (err) {
      const msg = handleApiError(err, "Unable to load documents.");
      if (msg) setLoadError(msg);
    }
  }, [handleApiError]);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  // Documents indexing asynchronously in backend-ai flip from
  // 'processing' to 'indexed'/'failed' out of band — keep polling
  // (self-scheduling, not a fixed interval) only while at least one
  // is still in flight, so an idle page makes no network calls.
  useEffect(() => {
    if (!documents) return;
    const hasProcessing = documents.some((d) => d.status === "processing");
    if (!hasProcessing) return;
    const timer = window.setTimeout(() => void refreshDocuments(), 3000);
    return () => window.clearTimeout(timer);
  }, [documents, refreshDocuments]);

  // Keep the open drawer's document in sync with the polled list
  // (e.g. watching a document you uploaded flip to 'indexed' live).
  useEffect(() => {
    if (!selectedDoc || !documents) return;
    const fresh = documents.find((d) => d.id === selectedDoc.id);
    if (fresh && fresh !== selectedDoc) setSelectedDoc(fresh);
  }, [documents, selectedDoc]);

  const filteredDocs = useMemo(() => {
    if (!documents) return [];
    return documents.filter((doc) => {
      const matchesSearch = doc.filename.toLowerCase().includes(search.trim().toLowerCase());
      const matchesType = typeFilter === "all" || doc.file_type === typeFilter;
      const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
      return matchesSearch && matchesType && matchesStatus;
    });
  }, [documents, search, typeFilter, statusFilter]);

  function openDoc(doc: DocumentResponse) {
    setSelectedDoc(doc);
    setDrawerTab("Overview");
  }

  function triggerUpload() {
    fileInputRef.current?.click();
  }

  async function handleFileSelected(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file next time
    if (!file) return;
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!(ALLOWED_DOCUMENT_EXTENSIONS as readonly string[]).includes(ext)) {
      setLoadError(
        `Unsupported file type ".${ext}". Allowed: ${ALLOWED_DOCUMENT_EXTENSIONS.join(", ")}`,
      );
      return;
    }
    setUploading(true);
    try {
      await apiClient.uploadDocument(file);
      await refreshDocuments();
    } catch (err) {
      const msg = handleApiError(err, "Unable to upload document.");
      if (msg) setLoadError(msg);
    } finally {
      setUploading(false);
    }
  }

  async function handleReindex(doc: DocumentResponse) {
    setRowBusy((m) => ({ ...m, [doc.id]: true }));
    try {
      await apiClient.reindexDocument(doc.id);
      await refreshDocuments();
    } catch (err) {
      const msg = handleApiError(err, "Unable to reindex document.");
      if (msg) setLoadError(msg);
    } finally {
      setRowBusy((m) => ({ ...m, [doc.id]: false }));
    }
  }

  async function handleDelete(doc: DocumentResponse) {
    const ok = window.confirm(`Delete ${doc.filename}? This cannot be undone.`);
    if (!ok) return;
    setRowBusy((m) => ({ ...m, [doc.id]: true }));
    try {
      await apiClient.deleteDocument(doc.id);
      if (selectedDoc?.id === doc.id) setSelectedDoc(null);
      await refreshDocuments();
    } catch (err) {
      const msg = handleApiError(err, "Unable to delete document.");
      if (msg) setLoadError(msg);
    } finally {
      setRowBusy((m) => ({ ...m, [doc.id]: false }));
    }
  }

  function canDeleteDoc(doc: DocumentResponse): boolean {
    return canDeleteAny || (canDeleteOwn && doc.uploaded_by === user.id);
  }

  return (
    <div className="aegis-kb">
      <PageHeader
        title="Knowledge Base"
        subtitle="Manage your documents and content"
        actions={
          canUpload ? (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPT_ATTR}
                hidden
                onChange={(e) => void handleFileSelected(e)}
              />
              <Button variant="primary" onClick={triggerUpload} loading={uploading}>
                <UploadIcon /> Upload Documents
              </Button>
            </>
          ) : undefined
        }
      />

      {loadError && (
        <div className="aegis-banner aegis-banner--error" role="alert">
          {loadError}
          <button
            type="button"
            className="aegis-banner-dismiss"
            onClick={() => setLoadError(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="aegis-tabs">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            className={`aegis-tabs__tab ${tab === t ? "aegis-tabs__tab--active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </div>

      {tab !== "Documents" ? (
        <div className="aegis-panel">
          <div className="aegis-empty-state">
            {tab} view is coming soon — check back after this ships.
          </div>
        </div>
      ) : (
        <>
          <div className="aegis-kb__filters">
            <label className="aegis-kb__search">
              <SearchIcon className="aegis-kb__search-icon" />
              <input
                type="text"
                placeholder="Search documents..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <select
              className="aegis-select"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <option value="all">All types</option>
              {ALLOWED_DOCUMENT_EXTENSIONS.map((ext) => (
                <option key={ext} value={ext}>
                  {ext.toUpperCase()}
                </option>
              ))}
            </select>
            <select
              className="aegis-select"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="processing">Processing</option>
              <option value="indexed">Indexed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="aegis-panel aegis-kb__table-panel">
            <div className="aegis-table-wrap">
              <table className="aegis-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Size</th>
                    <th>Last Updated</th>
                    <th aria-label="Actions" />
                  </tr>
                </thead>
                <tbody>
                  {documents === null && !loadError && (
                    <tr>
                      <td colSpan={7}>
                        <div className="aegis-empty-state">Loading documents…</div>
                      </td>
                    </tr>
                  )}
                  {filteredDocs.map((doc) => {
                    const busy = !!rowBusy[doc.id];
                    return (
                      <tr
                        key={doc.id}
                        data-clickable="true"
                        aria-busy={busy || undefined}
                        onClick={() => openDoc(doc)}
                      >
                        <td>
                          <div className="aegis-kb__name-cell">
                            <span className="aegis-ext-badge">{doc.file_type.toUpperCase()}</span>
                            {doc.filename}
                          </div>
                        </td>
                        <td>{doc.file_type.toUpperCase()}</td>
                        <td>
                          <span className={`aegis-badge ${statusBadgeClass(doc.status)}`}>
                            {statusLabel(doc.status)}
                          </span>
                        </td>
                        <td>{doc.chunk_count ?? "—"}</td>
                        <td>{formatBytes(doc.size_bytes)}</td>
                        <td>{formatDate(doc.updated_at)}</td>
                        <td>
                          <div className="aegis-kb__row-actions">
                            {canReindex && (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={busy || doc.status === "processing"}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  void handleReindex(doc);
                                }}
                              >
                                Reindex
                              </Button>
                            )}
                            {canDeleteDoc(doc) && (
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={busy}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  void handleDelete(doc);
                                }}
                              >
                                Delete
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                  {documents !== null && filteredDocs.length === 0 && (
                    <tr>
                      <td colSpan={7}>
                        <div className="aegis-empty-state">
                          {documents.length === 0
                            ? canUpload
                              ? "No documents yet. Click Upload Documents to add the first one."
                              : "No documents yet."
                            : "No documents match your filters."}
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {selectedDoc && (
        <div className="aegis-kb-drawer" role="dialog" aria-label={`${selectedDoc.filename} details`}>
          <div className="aegis-kb-drawer__backdrop" onClick={() => setSelectedDoc(null)} />
          <div className="aegis-kb-drawer__panel">
            <div className="aegis-kb-drawer__header">
              <div className="aegis-kb-drawer__title">
                <span className="aegis-ext-badge">{selectedDoc.file_type.toUpperCase()}</span>
                {selectedDoc.filename}
                <span className={`aegis-badge ${statusBadgeClass(selectedDoc.status)}`}>
                  {statusLabel(selectedDoc.status)}
                </span>
              </div>
              <button
                type="button"
                className="aegis-kb-drawer__close"
                onClick={() => setSelectedDoc(null)}
                aria-label="Close"
              >
                <CloseIcon />
              </button>
            </div>

            <div className="aegis-tabs aegis-kb-drawer__tabs">
              {DRAWER_TABS.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`aegis-tabs__tab ${drawerTab === t ? "aegis-tabs__tab--active" : ""}`}
                  onClick={() => setDrawerTab(t)}
                >
                  {t}
                </button>
              ))}
            </div>

            {drawerTab === "Overview" ? (
              <div className="aegis-kb-drawer__body">
                <div className="aegis-kb-drawer__meta-col aegis-kb-drawer__meta-col--full">
                  {selectedDoc.status === "failed" && selectedDoc.error_message && (
                    <section>
                      <h3>Error</h3>
                      <p className="aegis-kb-drawer__error">{selectedDoc.error_message}</p>
                    </section>
                  )}
                  <section>
                    <h3>Statistics</h3>
                    <div className="aegis-kb-drawer__stats">
                      <div>
                        <span className="aegis-kb-drawer__stat-value">
                          {selectedDoc.chunk_count ?? "—"}
                        </span>
                        <span className="aegis-kb-drawer__stat-label">Chunks</span>
                      </div>
                      <div>
                        <span className="aegis-kb-drawer__stat-value">
                          {formatBytes(selectedDoc.size_bytes)}
                        </span>
                        <span className="aegis-kb-drawer__stat-label">Size</span>
                      </div>
                      <div>
                        <span className="aegis-kb-drawer__stat-value">
                          {selectedDoc.file_type.toUpperCase()}
                        </span>
                        <span className="aegis-kb-drawer__stat-label">Type</span>
                      </div>
                    </div>
                  </section>
                  <section>
                    <h3>Content Hash</h3>
                    <p className="aegis-kb-drawer__mono">{selectedDoc.content_hash ?? "—"}</p>
                  </section>
                  <section>
                    <h3>Uploaded</h3>
                    <p>
                      {formatDate(selectedDoc.created_at)}
                      {selectedDoc.uploaded_by === user.id && " (you)"}
                    </p>
                  </section>
                  <section>
                    <h3>Last Indexed</h3>
                    <p>{selectedDoc.indexed_at ? formatDate(selectedDoc.indexed_at) : "—"}</p>
                  </section>
                </div>
              </div>
            ) : (
              <div className="aegis-empty-state">{drawerTab} view is coming soon.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

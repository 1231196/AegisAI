import { useCallback } from "react";
import type { ReactNode } from "react";
import "./Sidebar.css";
import AegisLogo from "../assets/logo.png";
import {
  hasPermission,
  isCustomer,
  isPlatformAdmin,
  type Permission,
} from "../api/client";

/**
 * Nav id set. Each entry has to be a string; for items that are
 * actually routed, the value MUST be a valid AuthContext Screen
 * (the call site in App.tsx casts to Screen). Placeholder items
 * use distinctive non-Screen values (e.g. ``"briefs"``) and are
 * filtered out of ``onNavigate`` because their click handler is
 * a no-op.
 */
type NavId = string;
interface NavItem {
  id: NavId;
  label: string;
  icon: ReactNode;
  badge?: string;
  /** When set, clicking on this item is a no-op (UI option for items
   *  that are not yet routed to a real screen). */
  placeholder?: boolean;
  /** Some admin items are gated by a permission rather than a
   *  coarse role: e.g. Organisations requires ``manage_all_organizations``
   *  which is granted only to ``platform_admin``. Rendered below the
   *  admin section divider but only visible when the caller has the
   *  named permission. */
  requiresPermission?: Permission;
}

/**
 * Staff nav items — the operator dashboard surfaces (tickets,
 * knowledge base, analytics, etc.). Customer accounts see NONE of
 * these; the customer landing renders a completely different
 * surface (``CustomerPortalPage``) which has its own minimal nav.
 *
 * Kept as a constant so the visible-on-customer filter is a single
 * negated role check, not a per-item allow-list.
 */
const NAV_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: <DashboardIcon /> },
  { id: "briefs", label: "AI Briefs", icon: <BriefIcon />, badge: "5", placeholder: true },
  { id: "console", label: "Agent Console", icon: <ConsoleIcon />, badge: "3", placeholder: true },
  { id: "tickets", label: "Tickets", icon: <TicketIcon />, badge: "12", placeholder: true },
  { id: "knowledge", label: "Knowledge Base", icon: <KBIcon />, placeholder: true },
  { id: "analytics", label: "Analytics", icon: <ChartIcon />, placeholder: true },
  { id: "reports", label: "Reports", icon: <ReportIcon />, placeholder: true },
];

/**
 * Customer nav items. Visible only when the caller's role is
 * ``customer``. The Customer Portal page surfaces each of these as
 * a tab/section in the page body; the sidebar item just provides the
 * top-level visual anchor.
 */
const CUSTOMER_NAV_ITEMS: NavItem[] = [
  { id: "chat", label: "AI Assistant", icon: <ChatIcon /> },
  { id: "conversations", label: "My Conversations", icon: <ConversationIcon /> },
];

// Admin-only items. Appended under a labelled section divider when the
// caller has admin (tenant OR cross-tenant) scope. Kept separate so the
// regular nav order is stable (item positions don't shift as admin
// status toggles). ``requiresPermission`` items render only when the
// caller has the named permission; otherwise they're hidden entirely.
const ADMIN_ITEMS: NavItem[] = [
  {
    id: "users",
    label: "User Management",
    icon: <UsersIcon />,
    requiresPermission: "manage_users",
  },
  {
    id: "organizations",
    label: "Organisations",
    icon: <BuildingIcon />,
    requiresPermission: "manage_all_organizations",
  },
  { id: "settings", label: "Settings", icon: <CogIcon />, placeholder: true },
];

interface SidebarProps {
  role?: string;
  /**
   * Callers should pass the live permission set from AuthContext when
   * it's non-empty (preferred), and the fallback is the optimistic
   * front-end mirror. An empty ``grantedPermissions`` array means
   * "trust the role string" — the optimistic path.
   */
  grantedPermissions?: readonly string[];
  activeId?: string;
  /**
   * Navigation callback. Typed ``string`` so the Sidebar doesn't
   * have to forward-import AuthContext's Screen union. The single
   * call site in App.tsx casts to Screen before delegating to
   * ``auth.goToScreen``.
   */
  onNavigate?: (id: string) => void;
}

export function Sidebar({
  role,
  grantedPermissions,
  activeId = "dashboard",
  onNavigate,
}: SidebarProps) {
  const callerIsCustomer = isCustomer(role);
  // Admin section: any admin-scope role gets the section to render;
  // per-item permission gates filter further. We DELIBERATELY key
  // the section-level gate off ``manage_users`` + an ``isPlatformAdmin``
  // fallback so a freshly-promoted platform_admin still sees the
  // section even while the permissions array is empty mid-hydrate.
  const callerHasAdminScope =
    hasPermission(role, "manage_users", grantedPermissions) ||
    isPlatformAdmin(role);
  const visibleAdminItems = ADMIN_ITEMS.filter((item) => {
    if (!item.requiresPermission) return true;
    return hasPermission(role, item.requiresPermission, grantedPermissions);
  });
  const renderItem = useCallback(
    (item: NavItem) => {
      const active = item.id === activeId;
      const cls = [
        "aegis-sidebar__nav-item",
        active ? "aegis-sidebar__nav-item--active" : "",
        item.placeholder ? "aegis-sidebar__nav-item--placeholder" : "",
      ]
        .filter(Boolean)
        .join(" ");
      return (
        <button
          key={item.id}
          type="button"
          className={cls}
          aria-current={active ? "page" : undefined}
          aria-disabled={item.placeholder ? "true" : undefined}
          title={item.placeholder ? "Coming soon" : undefined}
          disabled={item.placeholder}
          onClick={item.placeholder ? undefined : () => onNavigate?.(item.id)}
        >
          <span
            className={`aegis-sidebar__nav-dot ${active ? "aegis-sidebar__nav-dot--active" : ""}`}
            aria-hidden="true"
          />
          <span className="aegis-sidebar__nav-icon">{item.icon}</span>
          <span className="aegis-sidebar__nav-label">{item.label}</span>
          {item.badge != null && (
            <span className="aegis-sidebar__nav-badge">{item.badge}</span>
          )}
        </button>
      );
    },
    [activeId, onNavigate],
  );

  return (
    <aside className="aegis-sidebar">
      <div className="aegis-sidebar__brand">
        <img src={AegisLogo} alt="Aegis Logo" height="160" width="160" />
        <div className="aegis-sidebar__brand-text">
        </div>
      </div>

      <nav className="aegis-sidebar__nav" aria-label="Primary">
        {/* Staff nav: hidden for customers. The Customer Portal
            renders its own minimal nav below so customer accounts
            do not see operator-only surfaces. */}
        {callerIsCustomer
          ? CUSTOMER_NAV_ITEMS.map(renderItem)
          : NAV_ITEMS.map(renderItem)}

        {callerHasAdminScope && visibleAdminItems.length > 0 && (
          <>
            <div className="aegis-sidebar__section-label">Admin</div>
            {visibleAdminItems.map(renderItem)}
          </>
        )}
      </nav>

      <div className="aegis-sidebar__footer">
        <div className="aegis-sidebar__footer-row">
          <span className="aegis-sidebar__footer-text">v1.0.0</span>
        </div>
        <div className="aegis-sidebar__footer-row">
          <span className="aegis-sidebar__footer-text aegis-sidebar__footer-text--muted">
            © 2026 Aegis AI
          </span>
        </div>
      </div>
    </aside>
  );
}

/* --- compact inline icons (1.5 stroke, currentColor) --- */

function DashboardIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <rect x="2.5" y="2.5" width="6.5" height="6.5" rx="1.2" />
      <rect x="11" y="2.5" width="6.5" height="6.5" rx="1.2" />
      <rect x="2.5" y="11" width="6.5" height="6.5" rx="1.2" />
      <rect x="11" y="11" width="6.5" height="6.5" rx="1.2" />
    </svg>
  );
}
function BriefIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 5h14v10H3z" />
      <path d="M7 5V3h6v2" />
      <path d="M3 9h14" />
	</svg>
  );
}
function ConsoleIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 4h14v12H3z" />
      <path d="M6 8l3 2-3 2" />
      <path d="M11 12h4" />
    </svg>
  );
}
function TicketIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 6.5V4h14v2.5a2 2 0 0 0 0 4V13a2 2 0 0 0 0 4V19H3v-2a2 2 0 0 0 0-4v-2.5a2 2 0 0 0 0-4z" />
      <path d="M9 4v12" />
    </svg>
  );
}
function KBIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M10 2a4 4 0 0 1 4 4v2a4 4 0 1 1-8 0V6a4 4 0 0 1 4-4z" />
      <path d="M4 18v-2a6 6 0 0 1 12 0v2" />
    </svg>
  );
}
function ChartIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round">
      <path d="M3 16h14" />
      <path d="M5 13V9" />
      <path d="M9 13V5" />
      <path d="M13 13V7" />
      <path d="M17 13v-3" />
    </svg>
  );
}
function UsersIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="2.6" />
      <path d="M3 16v-1.4a4 4 0 0 1 4-4h0a4 4 0 0 1 4 4V16" />
      <circle cx="14" cy="6.5" r="2" />
      <path d="M14 11.5h.6a3.4 3.4 0 0 1 3.4 3.4V16" />
    </svg>
  );
}
function BuildingIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 17V4h9v13" />
      <path d="M13 17V8h4v9" />
      <path d="M6 7h2M6 10h2M6 13h2M9 7h2M9 10h2M9 13h2" />
      <path d="M3 17h15" />
    </svg>
  );
}
function ReportIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5}>
      <path d="M5 3h7l4 4v10H5z" />
      <path d="M12 3v4h4" />
      <path d="M8 11h6" />
      <path d="M8 14h4" />
    </svg>
  );
}
function CogIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <circle cx="10" cy="10" r="2.4" />
      <path d="M10 2.5v2.4M10 15.1v2.4M17.5 10h-2.4M4.9 10H2.5M15.3 4.7l-1.7 1.7M6.4 13.6l-1.7 1.7M15.3 15.3l-1.7-1.7M6.4 6.4 4.7 4.7" />
    </svg>
  );
}
function ChatIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 4h12a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H7l-4 3V6a2 2 0 0 1 0-2z" />
      <path d="M7 9h6" />
      <path d="M7 12h4" />
    </svg>
  );
}
function ConversationIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="14" height="11" rx="2" />
      <path d="M6 17h8" />
      <path d="M10 14v3" />
      <path d="M7 8h6" />
    </svg>
  );
}

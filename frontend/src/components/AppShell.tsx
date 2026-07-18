import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import type { UserResponse } from "../api/client";
import "./AppShell.css";

interface AppShellProps {
  children: ReactNode;
  topbar?: ReactNode;
  user?: UserResponse | null;
  /**
   * Live permission set from AuthContext. ``Sidebar`` prefers this
   * over the optimistic ``ROLE_PERMISSIONS`` mirror when non-empty.
   */
  grantedPermissions?: readonly string[];
  activeId?: string;
  /** Navigation callback. Caller is responsible for casting the
   *  string id to the AuthContext Screen union it expects. */
  onNavigate?: (id: string) => void;
}

export function AppShell({
  children,
  topbar,
  user,
  grantedPermissions,
  activeId,
  onNavigate,
}: AppShellProps) {
  return (
    <div className="aegis-app-shell">
      <Sidebar
        role={user?.role}
        grantedPermissions={grantedPermissions}
        activeId={activeId}
        onNavigate={onNavigate}
      />
      <div className="aegis-app-shell__layout">
        {topbar && <header className="aegis-app-shell__topbar">{topbar}</header>}
        <main className="aegis-app-shell__main">{children}</main>
      </div>
    </div>
  );
}

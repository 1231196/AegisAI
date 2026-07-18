import type { ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import "./AuthShell.css";

interface AuthShellProps {
  children: ReactNode;
}

export function AuthShell({ children }: AuthShellProps) {
  return (
    <div className="aegis-auth-shell">
      <Sidebar />
      <main className="aegis-auth-shell__main">
        <div className="aegis-auth-shell__panel">
          {children}
        </div>
      </main>
    </div>
  );
}

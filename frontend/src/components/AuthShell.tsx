import type { ReactNode } from "react";
import { AuthBrandPanel } from "./AuthBrandPanel";
import "./AuthShell.css";

interface AuthShellProps {
  children: ReactNode;
}

export function AuthShell({ children }: AuthShellProps) {
  return (
    <div className="aegis-auth-shell">
      <AuthBrandPanel />
      <main className="aegis-auth-shell__main">
        <div className="aegis-auth-shell__panel">
          {children}
        </div>
      </main>
    </div>
  );
}

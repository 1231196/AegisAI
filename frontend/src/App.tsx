import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AppShell } from "./components/AppShell";
import { AuthShell } from "./components/AuthShell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Topbar } from "./components/Topbar";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CustomerPortalPage } from "./pages/CustomerPortalPage";
import { UsersPage } from "./pages/UsersPage";
import { OrganizationsPage } from "./pages/OrganizationsPage";
import { AiChatPage } from "./pages/AiChatPage";
import { KnowledgeBasePage } from "./pages/KnowledgeBasePage";
import { AiAgentPage } from "./pages/AiAgentPage";
import { McpToolsPage } from "./pages/McpToolsPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { MonitoringPage } from "./pages/MonitoringPage";
import { hasPermission, isCustomer } from "./api/client";
import type { Screen } from "./contexts/AuthContext";
import "./App.css";

// Staff-only screens backed by mock data (no backend yet). Kept as a
// Set so the routing switch below has a single source of truth for
// "is this one of the new static pages" instead of repeating the
// literal list in both the activeId and page-selection branches.
const MOCK_STAFF_SCREENS = new Set<Screen>([
  "aiChat",
  "knowledgeBase",
  "aiAgent",
  "mcpTools",
  "analytics",
  "evaluation",
  "monitoring",
]);

function AppInner() {
  const auth = useAuth();

  if (auth.isLoading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          color: "var(--text-secondary)",
          fontSize: 14,
        }}
      >
        Loading Aegis AI…
      </div>
    );
  }

  if (auth.isAuthenticated && !auth.pendingVerification) {
    // Belt-and-braces role/permission gates. If the screen state was
    // carried over from a stale role (e.g. a stale admin-attached
    // screen after the caller's role was downgraded) the user lands
    // on their role-appropriate landing instead of an unauthorised
    // page. ``hasPermission`` prefers the live permission set from
    // AuthContext (authoritative); falls back to the optimistic
    // front-end mirror in ``hasPermission`` itself.
    const callerIsCustomer = isCustomer(auth.user?.role);
    const allowUsers =
      auth.screen === "users" &&
      hasPermission(auth.user?.role, "manage_users", auth.permissions);
    const allowOrganizations =
      auth.screen === "organizations" &&
      hasPermission(
        auth.user?.role,
        "manage_all_organizations",
        auth.permissions,
      );
    const allowCustomers =
      auth.screen === "chat" && callerIsCustomer;

    // Static/mock screens (AI Chat, Knowledge Base, etc.) are staff-only
    // and have no permission gate of their own — any non-customer lands
    // on whichever one is in auth.screen.
    const allowMockScreen =
      !callerIsCustomer && MOCK_STAFF_SCREENS.has(auth.screen);

    // Active sidebar item id:
    //   - customer chat page        → "chat"
    //   - users page (admin-scope)  → "users"
    //   - orgs  page (cross-tenant) → "organizations"
    //   - mock staff screen         → that screen's id
    //   - default               → "dashboard"
    //   - any gated-out screen    → caller role's landing
    let activeId: string;
    if (allowCustomers) {
      activeId = "chat";
    } else if (allowOrganizations) {
      activeId = "organizations";
    } else if (allowUsers) {
      activeId = "users";
    } else if (allowMockScreen) {
      activeId = auth.screen;
    } else {
      activeId = callerIsCustomer ? "chat" : "dashboard";
    }

    // Cast the Sidebar/AppShell's `(id: string) => void` callback
    // to AuthContext's stricter ``Screen``-typed ``goToScreen``.
    // Sidebar's full NavItem set includes placeholder ids (e.g.
    // ``"settings"``) that don't correspond to a real screen, but
    // those items have a no-op click handler so this closure is
    // only ever invoked with a real screen id.
    const shellProps = {
      user: auth.user,
      grantedPermissions: auth.permissions,
      activeId,
      onNavigate: (id: string) => auth.goToScreen(id as Screen),
      topbar: <Topbar user={auth.user} />,
    };

    // Page selection mirrors the sidebar-active id, but with a
    // belt-and-braces fallback to the role-appropriate landing if
    // the requested screen is gated out (e.g. an admin-attached
    // ``organizations`` screen on a freshly-demoted customer).
    let page: React.ReactNode;
    if (allowCustomers) {
      page = (
        <CustomerPortalPage
          user={auth.user!}
          onLogout={() => auth.logout()}
        />
      );
    } else if (allowOrganizations) {
      page = (
        <OrganizationsPage
          user={auth.user!}
          onRevoked={() => auth.goToScreen("dashboard")}
        />
      );
    } else if (allowUsers) {
      page = (
        <UsersPage
          user={auth.user!}
          onRevoked={() => auth.goToScreen("dashboard")}
        />
      );
    } else if (allowMockScreen && auth.screen === "aiChat") {
      page = <AiChatPage user={auth.user!} />;
    } else if (allowMockScreen && auth.screen === "knowledgeBase") {
      page = (
        <KnowledgeBasePage
          user={auth.user!}
          grantedPermissions={auth.permissions}
        />
      );
    } else if (allowMockScreen && auth.screen === "aiAgent") {
      page = <AiAgentPage />;
    } else if (allowMockScreen && auth.screen === "mcpTools") {
      page = <McpToolsPage />;
    } else if (allowMockScreen && auth.screen === "analytics") {
      page = <AnalyticsPage />;
    } else if (allowMockScreen && auth.screen === "evaluation") {
      page = <EvaluationPage />;
    } else if (allowMockScreen && auth.screen === "monitoring") {
      page = <MonitoringPage />;
    } else if (callerIsCustomer) {
      // Customer reached dashboard/organizations/users via stale
      // state — bounce to chat portal.
      page = (
        <CustomerPortalPage
          user={auth.user!}
          onLogout={() => auth.logout()}
        />
      );
    } else {
      page = (
        <DashboardPage
          user={auth.user}
          onLogout={() => auth.logout()}
        />
      );
    }

    return <AppShell {...shellProps}>{page}</AppShell>;
  }

  if (auth.pendingVerification) {
    return (
      <AuthShell>
        <VerifyEmailPage />
      </AuthShell>
    );
  }

  // Unauthenticated screen routing (uses auth.screen state).
  switch (auth.screen) {
    case "register":
      return (
        <AuthShell>
          <RegisterPage />
        </AuthShell>
      );
    case "login":
    default:
      return (
        <AuthShell>
          <LoginPage />
        </AuthShell>
      );
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppInner />
      </AuthProvider>
    </ErrorBoundary>
  );
}

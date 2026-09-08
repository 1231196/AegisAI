import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import type { UserResponse } from "../api/client";
import {
  ACTIVE_MODELS,
  DASHBOARD_STATS,
  LATEST_DOCUMENTS,
  RECENT_CONVERSATIONS,
  SYSTEM_HEALTH,
} from "../mocks/data";
import "./DashboardPage.css";

interface DashboardPageProps {
  user: UserResponse | null;
  onLogout: () => Promise<void>;
}

export function DashboardPage({ user, onLogout }: DashboardPageProps) {
  return (
    <div className="aegis-dashboard">
      <PageHeader title="Dashboard" subtitle="Overview of your platform" />

      <div className="aegis-dashboard__stat-grid">
        {DASHBOARD_STATS.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <div className="aegis-panel-grid">
        <section className="aegis-panel">
          <div className="aegis-panel__header">
            <h2 className="aegis-panel__title">Recent Conversations</h2>
            <button type="button" className="aegis-panel__link">View all</button>
          </div>
          <ul className="aegis-dashboard__list">
            {RECENT_CONVERSATIONS.map((row) => (
              <li className="aegis-dashboard__row" key={row.title}>
                <span className="aegis-dashboard__row-dot" aria-hidden="true" />
                <span className="aegis-dashboard__row-text">{row.title}</span>
                <span className="aegis-dashboard__row-meta">{row.time}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="aegis-panel">
          <div className="aegis-panel__header">
            <h2 className="aegis-panel__title">Latest Documents</h2>
            <button type="button" className="aegis-panel__link">View all</button>
          </div>
          <ul className="aegis-dashboard__list">
            {LATEST_DOCUMENTS.map((doc) => (
              <li className="aegis-dashboard__row" key={doc.name}>
                <span className="aegis-ext-badge">{doc.ext}</span>
                <span className="aegis-dashboard__row-text">{doc.name}</span>
                <span className="aegis-dashboard__row-meta">{doc.size} · {doc.time}</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="aegis-panel">
          <div className="aegis-panel__header">
            <h2 className="aegis-panel__title">Active Models</h2>
          </div>
          <ul className="aegis-dashboard__list">
            {ACTIVE_MODELS.map((model) => (
              <li className="aegis-dashboard__model-row" key={model.name}>
                <span className="aegis-dashboard__row-text">{model.name}</span>
                <div className="aegis-dashboard__model-bar">
                  <div
                    className="aegis-dashboard__model-bar-fill"
                    style={{ width: `${model.pct}%` }}
                  />
                </div>
                <span className="aegis-dashboard__row-meta">{model.pct}%</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="aegis-panel">
          <div className="aegis-panel__header">
            <h2 className="aegis-panel__title">System Health</h2>
            <span className="aegis-dashboard__health-meta">All systems operational</span>
          </div>
          <ul className="aegis-dashboard__list">
            {SYSTEM_HEALTH.map((svc) => (
              <li className="aegis-dashboard__row" key={svc.name}>
                <span className="aegis-dot aegis-dot--success" aria-hidden="true" />
                <span className="aegis-dashboard__row-text">{svc.name}</span>
                <span className="aegis-dashboard__row-meta">{svc.uptime}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="aegis-dashboard__signout-row">
        <span className="aegis-dashboard__account-meta">
          Signed in as {user?.username ?? "—"} · {user?.role ?? "member"}
        </span>
        <Button variant="secondary" onClick={() => void onLogout()}>
          Sign out
        </Button>
      </div>
    </div>
  );
}

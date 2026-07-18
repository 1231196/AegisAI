import { Button } from "../components/Button";
import type { UserResponse } from "../api/client";
import "./DashboardPage.css";

interface DashboardPageProps {
  user: UserResponse | null;
  onLogout: () => Promise<void>;
}

const STATS = [
  {
    label: "Open tickets",
    value: "12",
    meta: "+3 this week",
    trend: "up",
    accentClass: "",
  },
  {
    label: "AI briefs",
    value: "5",
    meta: "2 awaiting review",
    trend: "neutral",
    accentClass: "aegis-dashboard__card-accent--blue",
  },
  {
    label: "Active agents",
    value: "3",
    meta: "All healthy",
    trend: "up",
    accentClass: "aegis-dashboard__card-accent--green",
  },
  {
    label: "Knowledge articles",
    value: "142",
    meta: "7 updated",
    trend: "neutral",
    accentClass: "aegis-dashboard__card-accent--purple",
  },
];

const RECENT = [
  {
    dot: "",
    text: "Ticket #4821 (\"VPN intermittent for finance users\") auto-routed to support",
    meta: "12 min ago",
  },
  {
    dot: "aegis-dashboard__row-dot--blue",
    text: "AI brief flagged 3 anomalies in weekly ops report",
    meta: "1 h ago",
  },
  {
    dot: "aegis-dashboard__row-dot--purple",
    text: "Knowledge article \"Reset MFA for Okta\" updated",
    meta: "3 h ago",
  },
];

export function DashboardPage({ user, onLogout }: DashboardPageProps) {
  return (
    <div className="aegis-dashboard">
      <div className="aegis-dashboard__hero">
        <h1 className="aegis-dashboard__welcome">
          Welcome back, {user?.username?.split("@")[0] ?? "there"}
        </h1>
        <div className="aegis-dashboard__meta">
          Role
          <span className="aegis-dashboard__chip">{user?.role ?? "member"}</span>
          &middot;
          <span>org {user?.organization_id?.slice(0, 8) ?? "—"}</span>
        </div>
      </div>

      <div className="aegis-dashboard__grid">
        {STATS.map((stat) => (
          <div className="aegis-dashboard__card" key={stat.label}>
            <div className="aegis-dashboard__card-label">{stat.label}</div>
            <div className="aegis-dashboard__card-value">{stat.value}</div>
            <div
              className={`aegis-dashboard__card-meta ${
                stat.trend === "up" ? "aegis-dashboard__card-meta-up" : ""
              }`}
            >
              {stat.meta}
            </div>
            <span className={`aegis-dashboard__card-accent ${stat.accentClass}`} />
          </div>
        ))}
      </div>

      <section className="aegis-dashboard__panel">
        <h2 className="aegis-dashboard__panel-title">Recent activity</h2>
        {RECENT.length === 0 ? (
          <div className="aegis-dashboard__empty">
            Nothing yet — events from your agents and tickets will show up here.
          </div>
        ) : (
          RECENT.map((row, idx) => (
            <div className="aegis-dashboard__row" key={idx}>
              <span
                className={`aegis-dashboard__row-dot ${row.dot}`}
                aria-hidden="true"
              />
              <span className="aegis-dashboard__row-text">{row.text}</span>
              <span className="aegis-dashboard__row-meta">{row.meta}</span>
            </div>
          ))
        )}
      </section>

      <div className="aegis-dashboard__signout-row">
        <Button variant="secondary" onClick={() => void onLogout()}>
          Sign out
        </Button>
      </div>
    </div>
  );
}

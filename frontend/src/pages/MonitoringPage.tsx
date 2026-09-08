import { PageHeader } from "../components/PageHeader";
import { Sparkline } from "../components/Sparkline";
import { STAT_ICONS } from "../components/icons";
import { MONITORING_SERVICES, MONITORING_STATS } from "../mocks/data";
import "./MonitoringPage.css";

export function MonitoringPage() {
  return (
    <div className="aegis-monitoring">
      <PageHeader
        title="Monitoring"
        subtitle="Track system performance and infrastructure"
        actions={<span className="aegis-page-header__pill">Last 7 days</span>}
      />

      <div className="aegis-monitoring__stat-grid">
        {MONITORING_STATS.map((stat) => {
          const Icon = STAT_ICONS[stat.icon];
          return (
            <div className="aegis-stat-card aegis-monitoring__stat-card" key={stat.label}>
              <div className="aegis-stat-card__icon">
                <Icon />
              </div>
              <div className="aegis-stat-card__label">{stat.label}</div>
              <div className="aegis-stat-card__value">{stat.value}</div>
              <div
                className={`aegis-stat-card__meta ${
                  stat.deltaDirection === "up"
                    ? "aegis-stat-card__meta--up"
                    : "aegis-stat-card__meta--down"
                }`}
              >
                <span className="aegis-stat-card__delta">
                  {stat.deltaDirection === "up" ? "↑" : "↓"} {stat.delta}
                </span>
              </div>
              <Sparkline points={stat.points} variant="area" width={160} height={36} />
            </div>
          );
        })}
      </div>

      <section className="aegis-panel">
        <div className="aegis-panel__header">
          <h2 className="aegis-panel__title">Service Health</h2>
        </div>
        <div className="aegis-monitoring__service-grid">
          {MONITORING_SERVICES.map((svc) => (
            <div className="aegis-monitoring__service-card" key={svc.name}>
              <div className="aegis-monitoring__service-header">
                <span className="aegis-dot aegis-dot--success" aria-hidden="true" />
                <span className="aegis-monitoring__service-name">{svc.name}</span>
                <span className="aegis-badge aegis-badge--success">Healthy</span>
              </div>
              <Sparkline points={svc.points} variant="area" width={220} height={44} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

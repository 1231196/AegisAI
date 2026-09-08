import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { Sparkline } from "../components/Sparkline";
import { ANALYTICS_SERIES, ANALYTICS_STATS } from "../mocks/data";
import "./AnalyticsPage.css";

export function AnalyticsPage() {
  return (
    <div className="aegis-analytics">
      <PageHeader
        title="Analytics"
        subtitle="Track usage and performance metrics"
        actions={<span className="aegis-page-header__pill">Last 7 days</span>}
      />

      <div className="aegis-analytics__stat-grid">
        {ANALYTICS_STATS.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <section className="aegis-panel aegis-analytics__chart-panel">
        <div className="aegis-panel__header">
          <h2 className="aegis-panel__title">Requests Over Time</h2>
        </div>
        <div className="aegis-analytics__chart">
          <div className="aegis-analytics__y-axis">
            {ANALYTICS_SERIES.yLabels.map((label) => (
              <span key={label}>{label}</span>
            ))}
          </div>
          <div className="aegis-analytics__chart-body">
            <Sparkline
              points={ANALYTICS_SERIES.values}
              variant="area"
              width={720}
              height={220}
              className="aegis-analytics__sparkline"
            />
            <div className="aegis-analytics__x-axis">
              {ANALYTICS_SERIES.labels.map((label) => (
                <span key={label}>{label}</span>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { EVALUATION_STATS, EVAL_RUNS } from "../mocks/data";
import "./EvaluationPage.css";

export function EvaluationPage() {
  return (
    <div className="aegis-evaluation">
      <PageHeader
        title="Evaluation"
        subtitle="Monitor answer quality and model performance"
      />

      <div className="aegis-evaluation__stat-grid">
        {EVALUATION_STATS.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      <section className="aegis-panel">
        <div className="aegis-panel__header">
          <h2 className="aegis-panel__title">Recent Evaluation Runs</h2>
        </div>
        <div className="aegis-table-wrap">
          <table className="aegis-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Dataset</th>
                <th>Accuracy</th>
                <th>Faithfulness</th>
                <th>Date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {EVAL_RUNS.map((run) => (
                <tr key={run.id}>
                  <td className="aegis-evaluation__run-id">{run.id}</td>
                  <td>{run.dataset}</td>
                  <td>{run.accuracy}</td>
                  <td>{run.faithfulness}</td>
                  <td>{run.date}</td>
                  <td>
                    <span
                      className={`aegis-badge ${
                        run.status === "Passed" ? "aegis-badge--success" : "aegis-badge--error"
                      }`}
                    >
                      {run.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

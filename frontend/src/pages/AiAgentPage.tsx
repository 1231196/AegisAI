import { useState } from "react";
import { PageHeader } from "../components/PageHeader";
import { CheckIcon } from "../components/icons";
import { AGENT_DEFAULT_STEP_ID, AGENT_STEPS, AGENT_TASK } from "../mocks/data";
import "./AiAgentPage.css";

export function AiAgentPage() {
  const [selectedId, setSelectedId] = useState(AGENT_DEFAULT_STEP_ID);
  const selectedStep =
    AGENT_STEPS.find((s) => s.id === selectedId) ?? AGENT_STEPS[0];

  return (
    <div className="aegis-agent">
      <PageHeader
        title="AI Agent"
        subtitle="Visualize the agent's reasoning and actions"
      />

      <div className="aegis-agent__layout">
        <section className="aegis-panel aegis-agent__task-panel">
          <div className="aegis-panel__header">
            <h2 className="aegis-panel__title">Task</h2>
          </div>
          <p className="aegis-agent__task-text">{AGENT_TASK}</p>

          <ol className="aegis-agent__steps">
            {AGENT_STEPS.map((step, i) => (
              <li key={step.id} className="aegis-agent__step">
                <div className="aegis-agent__step-rail">
                  <span className="aegis-agent__step-dot" aria-hidden="true">
                    <CheckIcon />
                  </span>
                  {i < AGENT_STEPS.length - 1 && <span className="aegis-agent__step-line" />}
                </div>
                <button
                  type="button"
                  className={`aegis-agent__step-btn ${
                    step.id === selectedId ? "aegis-agent__step-btn--active" : ""
                  }`}
                  onClick={() => setSelectedId(step.id)}
                >
                  <div className="aegis-agent__step-title-row">
                    <span className="aegis-agent__step-title">{step.title}</span>
                    <span className="aegis-badge aegis-badge--success">{step.status}</span>
                  </div>
                  <p className="aegis-agent__step-desc">{step.description}</p>
                </button>
              </li>
            ))}
          </ol>
        </section>

        <section className="aegis-panel aegis-agent__detail-panel">
          <div className="aegis-panel__header">
            <h2 className="aegis-panel__title">Step Details</h2>
          </div>

          {selectedStep.detail.kind === "tool" ? (
            <div className="aegis-agent__detail">
              <div>
                <h3>Tool Call</h3>
                <code className="aegis-agent__tool-name">{selectedStep.detail.toolName}</code>
              </div>
              <div className="aegis-agent__detail-row">
                <span>Status</span>
                <span className="aegis-badge aegis-badge--success">{selectedStep.detail.status}</span>
              </div>
              <div className="aegis-agent__detail-row">
                <span>Latency</span>
                <span>{selectedStep.detail.latency}</span>
              </div>
              <div>
                <h3>Parameters</h3>
                <pre className="aegis-code">{selectedStep.detail.params}</pre>
              </div>
              <div>
                <h3>Result</h3>
                <p className="aegis-agent__result-text">{selectedStep.detail.result}</p>
              </div>
            </div>
          ) : (
            <div className="aegis-agent__detail">
              <h3>Summary</h3>
              <p className="aegis-agent__result-text">{selectedStep.detail.text}</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

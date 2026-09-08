import { PageHeader } from "../components/PageHeader";
import { MoreIcon, PlugIcon } from "../components/icons";
import { MCP_TOOLS } from "../mocks/data";
import "./McpToolsPage.css";

export function McpToolsPage() {
  return (
    <div className="aegis-mcp">
      <PageHeader title="MCP Tools" subtitle="Manage and monitor your MCP tools" />

      <div className="aegis-mcp__grid">
        {MCP_TOOLS.map((tool) => (
          <div className="aegis-panel aegis-mcp__card" key={tool.name}>
            <div className="aegis-mcp__card-header">
              <span className="aegis-mcp__card-icon" aria-hidden="true">
                <PlugIcon />
              </span>
              <button type="button" className="aegis-mcp__card-menu" aria-label="Tool actions">
                <MoreIcon />
              </button>
            </div>
            <code className="aegis-mcp__card-name">{tool.name}</code>
            <p className="aegis-mcp__card-desc">{tool.description}</p>
            <div className="aegis-mcp__card-footer">
              <span
                className={`aegis-dot ${tool.healthy ? "aegis-dot--success" : "aegis-dot--error"}`}
                aria-hidden="true"
              />
              <span className="aegis-mcp__card-status">
                {tool.healthy ? "Healthy" : "Down"}
              </span>
              <span className="aegis-mcp__card-latency">{tool.latency}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Static mock data for the screens that don't have a backend yet
 * (AI Chat, Knowledge Base, AI Agent, MCP Tools, Analytics, Evaluation,
 * Monitoring) plus the Dashboard's richer panels. Kept in one place so
 * page components stay focused on layout, not hardcoded numbers.
 */

// --- Dashboard -------------------------------------------------------

export type StatIcon =
  | "activity"
  | "document"
  | "chat"
  | "building"
  | "clock"
  | "dollar"
  | "token"
  | "target"
  | "cpu"
  | "memory"
  | "requests"
  | "error";

export interface DashboardStat {
  label: string;
  value: string;
  delta: string;
  deltaDirection: "up" | "down";
  meta: string;
  icon: StatIcon;
}

export const DASHBOARD_STATS: DashboardStat[] = [
  { label: "Total Requests", value: "42,104", delta: "16.3%", deltaDirection: "up", meta: "vs last 7 days", icon: "activity" },
  { label: "Documents Indexed", value: "2,103", delta: "12.5%", deltaDirection: "up", meta: "vs last 7 days", icon: "document" },
  { label: "Conversations", value: "1,231", delta: "15.1%", deltaDirection: "up", meta: "vs last 7 days", icon: "chat" },
  { label: "Organizations", value: "14", delta: "7.3%", deltaDirection: "up", meta: "Active organizations", icon: "building" },
  { label: "Avg. Latency", value: "721 ms", delta: "6.3%", deltaDirection: "up", meta: "vs last 7 days", icon: "clock" },
  { label: "Total Cost", value: "$143.21", delta: "6.4%", deltaDirection: "up", meta: "vs last 7 days", icon: "dollar" },
  { label: "Tokens Used", value: "12.4M", delta: "22.1%", deltaDirection: "up", meta: "vs last 7 days", icon: "token" },
  { label: "Answer Accuracy", value: "94%", delta: "3.2%", deltaDirection: "up", meta: "Faithfulness avg", icon: "target" },
];

export interface RecentConversation {
  title: string;
  time: string;
}
export const RECENT_CONVERSATIONS: RecentConversation[] = [
  { title: "Troubleshooting Payment Failure", time: "2 min ago" },
  { title: "How to configure Kubernetes Ingress?", time: "15 min ago" },
  { title: "API rate limit errors", time: "1 hour ago" },
  { title: "Database connection timeout", time: "4 hours ago" },
  { title: "Refund not processed", time: "1 day ago" },
];

export interface LatestDocument {
  name: string;
  ext: string;
  size: string;
  time: string;
}
export const LATEST_DOCUMENTS: LatestDocument[] = [
  { name: "Docker Deployment Guide.pdf", ext: "PDF", size: "12.4 MB", time: "2 min ago" },
  { name: "Kubernetes Best Practices.md", ext: "MD", size: "535 KB", time: "1 hour ago" },
  { name: "API Reference Guide.pdf", ext: "PDF", size: "8.7 MB", time: "3 hours ago" },
  { name: "Products data.csv", ext: "CSV", size: "2.1 MB", time: "5 hours ago" },
  { name: "Troubleshooting Guide.txt", ext: "TXT", size: "312 KB", time: "1 day ago" },
];

export interface ActiveModel {
  name: string;
  pct: number;
}
export const ACTIVE_MODELS: ActiveModel[] = [
  { name: "GPT-4o", pct: 62 },
  { name: "Claude 3.5 Sonnet", pct: 21 },
  { name: "Gemini 1.5 Pro", pct: 10 },
  { name: "Llama 3.1 70B", pct: 5 },
  { name: "Mistral 8x22B", pct: 2 },
];

export interface SystemHealthItem {
  name: string;
  uptime: string;
}
export const SYSTEM_HEALTH: SystemHealthItem[] = [
  { name: "API Backend", uptime: "99.9%" },
  { name: "AI Service", uptime: "99.3%" },
  { name: "PostgreSQL", uptime: "100%" },
  { name: "Qdrant", uptime: "99.9%" },
  { name: "Redis", uptime: "100%" },
  { name: "MCP Server", uptime: "99.7%" },
];

// --- AI Agent ------------------------------------------------------------

export type AgentStepDetail =
  | { kind: "text"; text: string }
  | {
      kind: "tool";
      toolName: string;
      status: "Success" | "Failed";
      latency: string;
      params: string;
      result: string;
    };

export interface AgentStep {
  id: string;
  title: string;
  status: "Completed";
  description: string;
  detail: AgentStepDetail;
}

export const AGENT_TASK = "Investigate payment failure for user john.doe@acme.com";

export const AGENT_STEPS: AgentStep[] = [
  {
    id: "planning",
    title: "Planning",
    status: "Completed",
    description: "Analyzed the following: identified required data sources and tool calls needed to answer the query.",
    detail: {
      kind: "text",
      text: "Broke the request down into: retrieve relevant knowledge base articles on error code PMT_001, then check the user's live payment status via the payments tool.",
    },
  },
  {
    id: "retrieve",
    title: "Retrieve Knowledge",
    status: "Completed",
    description: "Searched knowledge base for relevant information",
    detail: {
      kind: "tool",
      toolName: "knowledge.search()",
      status: "Success",
      latency: "342 ms",
      params: `{
  "query": "error code PMT_001",
  "top_k": 5
}`,
      result: "Found 3 relevant chunks across Payments Troubleshooting Guide.pdf and Payment Error Codes.xlsx.",
    },
  },
  {
    id: "tool-calling",
    title: "Tool Calling",
    status: "Completed",
    description: "Called the following tools to gather data",
    detail: {
      kind: "tool",
      toolName: "payments.status()",
      status: "Success",
      latency: "342 ms",
      params: `{
  "user_id": "usr_13390",
  "from_date": "2024-06-01",
  "to_date": "2024-08-18"
}`,
      result: "Payment method declined due to insufficient funds. Last successful transaction on 2024-08-12.",
    },
  },
  {
    id: "reasoning",
    title: "Reasoning",
    status: "Completed",
    description: "Analyzed results and formulated response",
    detail: {
      kind: "text",
      text: "Combined the tool result with knowledge base guidance on error code PMT_001 to determine the most likely cause and next steps.",
    },
  },
  {
    id: "final-answer",
    title: "Final Answer",
    status: "Completed",
    description: "Generated final response for the user",
    detail: {
      kind: "text",
      text: "Delivered a structured explanation of the payment failure with recommended remediation steps for the support agent to relay.",
    },
  },
];

export const AGENT_DEFAULT_STEP_ID = "tool-calling";

// --- MCP Tools -------------------------------------------------------------

export interface McpTool {
  name: string;
  description: string;
  latency: string;
  healthy: boolean;
}
export const MCP_TOOLS: McpTool[] = [
  { name: "knowledge.search()", description: "Search the knowledge base", latency: "342 ms", healthy: true },
  { name: "orders.search()", description: "Search customer orders", latency: "410 ms", healthy: true },
  { name: "payments.status()", description: "Check payment status", latency: "298 ms", healthy: true },
  { name: "logs.search()", description: "Search system logs", latency: "512 ms", healthy: true },
  { name: "users.search()", description: "Search users", latency: "276 ms", healthy: true },
  { name: "tickets.create()", description: "Create a support ticket", latency: "318 ms", healthy: true },
];

// --- Analytics ---------------------------------------------------------

export const ANALYTICS_STATS: DashboardStat[] = [
  { label: "Requests", value: "42,104", delta: "18.2%", deltaDirection: "up", meta: "vs last 7 days", icon: "activity" },
  { label: "Tokens", value: "12.4M", delta: "22.1%", deltaDirection: "up", meta: "vs last 7 days", icon: "token" },
  { label: "Cost", value: "$143.21", delta: "6.4%", deltaDirection: "up", meta: "vs last 7 days", icon: "dollar" },
  { label: "Avg. Latency", value: "721 ms", delta: "6.8%", deltaDirection: "up", meta: "vs last 7 days", icon: "clock" },
];

export const ANALYTICS_SERIES = {
  labels: ["May 12", "May 13", "May 14", "May 15", "May 16", "May 17", "May 18"],
  values: [3200, 4800, 4100, 5600, 6900, 5200, 7400],
  yLabels: ["8K", "6K", "4K", "2K"],
};

// --- Evaluation ----------------------------------------------------------

export const EVALUATION_STATS: DashboardStat[] = [
  { label: "Answer Accuracy", value: "94%", delta: "3.2%", deltaDirection: "up", meta: "Faithfulness avg", icon: "target" },
  { label: "Faithfulness", value: "96%", delta: "1.8%", deltaDirection: "up", meta: "vs last 7 days", icon: "target" },
  { label: "Groundedness", value: "91%", delta: "2.4%", deltaDirection: "up", meta: "vs last 7 days", icon: "target" },
  { label: "Eval Runs", value: "128", delta: "9", deltaDirection: "up", meta: "this week", icon: "activity" },
];

export interface EvalRun {
  id: string;
  dataset: string;
  accuracy: string;
  faithfulness: string;
  date: string;
  status: "Passed" | "Failed";
}
export const EVAL_RUNS: EvalRun[] = [
  { id: "EVL-1042", dataset: "Support QA v3", accuracy: "94%", faithfulness: "96%", date: "Aug 2, 2026", status: "Passed" },
  { id: "EVL-1041", dataset: "Support QA v3", accuracy: "91%", faithfulness: "93%", date: "Aug 1, 2026", status: "Passed" },
  { id: "EVL-1040", dataset: "Refund Policy", accuracy: "88%", faithfulness: "90%", date: "Jul 31, 2026", status: "Passed" },
  { id: "EVL-1039", dataset: "Support QA v2", accuracy: "79%", faithfulness: "82%", date: "Jul 30, 2026", status: "Failed" },
  { id: "EVL-1038", dataset: "Support QA v3", accuracy: "95%", faithfulness: "97%", date: "Jul 29, 2026", status: "Passed" },
  { id: "EVL-1037", dataset: "Refund Policy", accuracy: "92%", faithfulness: "94%", date: "Jul 28, 2026", status: "Passed" },
];

// --- Monitoring ----------------------------------------------------------

export interface MonitoringStat {
  label: string;
  value: string;
  delta: string;
  deltaDirection: "up" | "down";
  icon: StatIcon;
  points: number[];
}
export const MONITORING_STATS: MonitoringStat[] = [
  { label: "CPU Usage", value: "23%", delta: "18.2%", deltaDirection: "up", icon: "cpu", points: [12, 18, 15, 22, 19, 25, 23] },
  { label: "Memory Usage", value: "45%", delta: "22.1%", deltaDirection: "up", icon: "memory", points: [30, 34, 38, 36, 41, 43, 45] },
  { label: "API Requests", value: "5.2K reqs", delta: "6.4%", deltaDirection: "up", icon: "requests", points: [3.8, 4.1, 4.6, 4.3, 4.9, 5.0, 5.2] },
  { label: "Error Rate", value: "0.12%", delta: "6.8%", deltaDirection: "down", icon: "error", points: [0.22, 0.19, 0.2, 0.16, 0.15, 0.13, 0.12] },
];

export interface ServiceHealth {
  name: string;
  points: number[];
}
export const MONITORING_SERVICES: ServiceHealth[] = [
  { name: "PostgreSQL", points: [40, 55, 48, 60, 52, 58, 62] },
  { name: "Qdrant", points: [30, 42, 38, 45, 40, 48, 44] },
  { name: "Redis", points: [60, 58, 65, 62, 70, 66, 72] },
  { name: "MCP Server", points: [20, 28, 25, 30, 27, 33, 29] },
];

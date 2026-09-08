import AegisLogo from "../assets/logo.png";
import "./AuthBrandPanel.css";

interface Feature {
  title: string;
  icon: "rag" | "agents" | "security" | "tenant";
}

const FEATURES: Feature[] = [
  { title: "Retrieval Augmented Generation", icon: "rag" },
  { title: "Intelligent AI Agents", icon: "agents" },
  { title: "Enterprise Security", icon: "security" },
  { title: "Multi-tenant Architecture", icon: "tenant" },
];

/**
 * Left-column marketing panel for the auth screens (sign in / create
 * account / verify email). Replaces the real app Sidebar, which used
 * to render here — that's operator nav, not a brand panel, and made
 * no sense on an unauthenticated screen.
 */
export function AuthBrandPanel() {
  return (
    <div className="aegis-auth-brand">
      <div className="aegis-auth-brand__wordmark">
        <img src={AegisLogo} alt="" height="40" width="40" />
        <span className="aegis-gradient-text">Aegis AI</span>
      </div>
      <p className="aegis-auth-brand__tagline">
        Enterprise AI Assistant for Support &amp; Operations
      </p>

      <ul className="aegis-auth-brand__features">
        {FEATURES.map((f) => (
          <li key={f.title} className="aegis-auth-brand__feature">
            <span className="aegis-auth-brand__feature-icon" aria-hidden="true">
              <FeatureIcon kind={f.icon} />
            </span>
            {f.title}
          </li>
        ))}
      </ul>
    </div>
  );
}

function FeatureIcon({ kind }: { kind: Feature["icon"] }) {
  const common = {
    viewBox: "0 0 20 20",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.5,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (kind) {
    case "rag":
      return (
        <svg {...common}>
          <path d="M10 2a4 4 0 0 1 4 4v2a4 4 0 1 1-8 0V6a4 4 0 0 1 4-4z" />
          <path d="M4 18v-2a6 6 0 0 1 12 0v2" />
        </svg>
      );
    case "agents":
      return (
        <svg {...common}>
          <path d="M3 4h14v12H3z" />
          <path d="M6 8l3 2-3 2" />
          <path d="M11 12h4" />
        </svg>
      );
    case "security":
      return (
        <svg {...common}>
          <path d="M10 2.5 16 5v5c0 4-2.6 6.7-6 7.5-3.4-.8-6-3.5-6-7.5V5z" />
          <path d="M7.5 10 9.3 11.8 13 8" />
        </svg>
      );
    case "tenant":
      return (
        <svg {...common}>
          <path d="M4 17.5V3.5h8v14" />
          <path d="M12 8.5h4v9" />
          <path d="M6.2 6.5h1.2M6.2 9.5h1.2M6.2 12.5h1.2M9.2 6.5h1.2M9.2 9.5h1.2M9.2 12.5h1.2" />
          <path d="M2.5 17.5h15" />
        </svg>
      );
  }
}

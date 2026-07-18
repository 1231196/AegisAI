import { Button } from "../components/Button";
import type { UserResponse } from "../api/client";
import "./CustomerPortalPage.css";

interface CustomerPortalPageProps {
  user: UserResponse;
  onLogout: () => Promise<void>;
}

/**
 * Customer landing surface. Distinct from the staff ``DashboardPage``
 * because the operator-focused stats (open tickets, active agents,
 * knowledge article counts) leak information a customer is not
 * supposed to see — and the spec explicitly excludes customers from
 * "view logs", "search internal systems", and "manage documents".
 *
 * Out of scope for this turn: a real chat UI / conversation
 * timeline. This page is a calm, role-appropriate shell that will
 * defer to the chat orchestrator in a follow-up. The guard against
 * rendering operator surfaces is the important bit.
 */
export function CustomerPortalPage({ user, onLogout }: CustomerPortalPageProps) {
  const firstName = user.username.split("@")[0];
  return (
    <div className="aegis-customer-portal">
      <section className="aegis-customer-portal__hero">
        <div className="aegis-customer-portal__hero-text">
          <div className="aegis-customer-portal__eyebrow">Customer Portal</div>
          <h1 className="aegis-customer-portal__welcome">
            Welcome, {firstName}
          </h1>
          <p className="aegis-customer-portal__subtitle">
            Ask questions, browse your past conversations, and upload files
            for context — all from one calm workspace.
          </p>
        </div>
        <div className="aegis-customer-portal__meta">
          <span className="aegis-customer-portal__chip">{user.role}</span>
          <span className="aegis-customer-portal__chip aegis-customer-portal__chip--muted">
            org {user.organization_id.slice(0, 8)}
          </span>
        </div>
      </section>

      <div className="aegis-customer-portal__grid">
        <article className="aegis-customer-portal__card aegis-customer-portal__card--accent">
          <div className="aegis-customer-portal__card-eyebrow">Available now</div>
          <h2 className="aegis-customer-portal__card-title">AI Assistant</h2>
          <p className="aegis-customer-portal__card-body">
            Start a conversation, attach a file for context, and download
            the generated answer with cited sources.
          </p>
          <div className="aegis-customer-portal__card-actions">
            <Button variant="primary" size="md" disabled>
              Open chat (coming soon)
            </Button>
          </div>
        </article>

        <article className="aegis-customer-portal__card">
          <div className="aegis-customer-portal__card-eyebrow">Library</div>
          <h2 className="aegis-customer-portal__card-title">My Conversations</h2>
          <p className="aegis-customer-portal__card-body">
            Browse and resume your past conversations with the assistant —
            no logs, no internal systems, just your own thread history.
          </p>
          <div className="aegis-customer-portal__card-actions">
            <Button variant="secondary" size="md" disabled>
              View library (coming soon)
            </Button>
          </div>
        </article>

        <article className="aegis-customer-portal__card">
          <div className="aegis-customer-portal__card-eyebrow">Files</div>
          <h2 className="aegis-customer-portal__card-title">File Uploads</h2>
          <p className="aegis-customer-portal__card-body">
            Drop a PDF or text note into a conversation for context. Files
            stay scoped to your conversations and are never shared across
            organisations.
          </p>
          <div className="aegis-customer-portal__card-actions">
            <Button variant="secondary" size="md" disabled>
              Upload (coming soon)
            </Button>
          </div>
        </article>
      </div>

      <section className="aegis-customer-portal__permissions">
        <h2 className="aegis-customer-portal__permissions-title">
          Your accessible features
        </h2>
        <ul className="aegis-customer-portal__permissions-list">
          <li>Chat with the AI Assistant</li>
          <li>View your own conversation history</li>
          <li>Upload files for context (per conversation)</li>
          <li>See cited sources used in answers</li>
          <li>Download generated answers</li>
        </ul>
      </section>

      <div className="aegis-customer-portal__signout-row">
        <Button variant="secondary" onClick={() => void onLogout()}>
          Sign out
        </Button>
      </div>
    </div>
  );
}

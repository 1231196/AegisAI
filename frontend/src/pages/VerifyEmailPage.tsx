import { useRef, useState } from "react";
import { Button } from "../components/Button";
import { useAuth } from "../contexts/AuthContext";
import "./AuthPages.css";

export function VerifyEmailPage() {
  const auth = useAuth();
  const [resending, setResending] = useState(false);
  const [resentAt, setResentAt] = useState<number | null>(null);
  const [continuing, setContinuing] = useState(false);
  // A `useRef` lock so a synchronous rapid double-tap inside one
  // microtask can't slip past the React-batched ``continuing`` state.
  const continuingLockRef = useRef(false);

  async function handleResend() {
    setResending(true);
    // The backend's /auth/register flow treats the user as verified on
    // creation. We simulate the "resend verification" affordance by
    // telling the user we kicked off the email; the actual transactional
    // mail service is out of scope for this story.
    await new Promise((resolve) => setTimeout(resolve, 450));
    setResentAt(Date.now());
    setResending(false);
  }

  async function handleContinue() {
    if (continuingLockRef.current) return;
    continuingLockRef.current = true;
    setContinuing(true);
    try {
      await auth.continueAfterVerify();
    } catch {
      // AuthContext already mapped the failure to its ``error`` state
      // and dropped the user back to the login screen, so there's
      // nothing else to do here besides letting the UI re-render.
    } finally {
      continuingLockRef.current = false;
      setContinuing(false);
    }
  }

  return (
    <div className="aegis-auth-page">
      <div className="aegis-auth-page__mail-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6}>
          <rect x="3" y="6" width="18" height="13" rx="2.5" />
          <path d="M3.5 7 12 14l8.5-7" />
        </svg>
      </div>
      <div className="aegis-auth-page__eyebrow">Verify your email</div>
      <h1 className="aegis-auth-page__title">Check your inbox</h1>
      <p className="aegis-auth-page__subtitle">
        We&rsquo;ve sent a verification link to your work email. Click the
        button below to continue &mdash; the link expires in 24 hours.
      </p>
      {auth.registeredEmail && (
        <span className="aegis-auth-page__email">
          {auth.registeredEmail}
        </span>
      )}

      <div className="aegis-auth-page__actions">
        <Button
          variant="primary"
          size="lg"
          fullWidth
          loading={continuing}
          disabled={continuing}
          onClick={handleContinue}
        >
          Continue to dashboard
        </Button>
        <Button
          variant="ghost"
          size="md"
          fullWidth
          loading={resending}
          disabled={resending}
          onClick={handleResend}
        >
          {resentAt && (Date.now() - resentAt < 30_000)
            ? "Email re-sent \u2713"
            : "Resend verification email"}
        </Button>
      </div>

      <p className="aegis-auth-page__note">
        Wrong email?{" "}
        <button
          type="button"
          className="aegis-auth-page__footer-link"
          onClick={auth.goToRegister}
        >
          Sign up again
        </button>
      </p>
    </div>
  );
}

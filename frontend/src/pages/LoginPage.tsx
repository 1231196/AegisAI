import { useState } from "react";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { PasswordInput } from "../components/PasswordInput";
import { useAuth } from "../contexts/AuthContext";
import "./AuthPages.css";

export function LoginPage() {
  const auth = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = email.trim().length > 0 && password.length > 0 && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await auth.login(email.trim(), password);
    } catch {
      // error already stored in auth.error by AuthContext.login
    } finally {
      setSubmitting(false);
    }
  }

  // Auth-context global error is rendered below; per-field validation
  // would just duplicate it, so we keep the input driven by HTML5
  // semantics (``required``, ``autoComplete``) and ``noValidate`` form.
  void auth.error;

  return (
    <div className="aegis-auth-page">
      <div className="aegis-auth-page__eyebrow">Continue</div>
      <h1 className="aegis-auth-page__title">Welcome back</h1>
      <p className="aegis-auth-page__subtitle">
        Sign in to continue to your Aegis AI workspace.
      </p>

      <form
        onSubmit={handleSubmit}
        className="aegis-auth-page__form"
        noValidate
      >
        <div className="aegis-auth-page__form-fields">
          <Input
            type="email"
            label="Email"
            placeholder="you@company.com"
            autoComplete="email"
            autoFocus
            required
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (auth.error) auth.clearError();
            }}
          />
          <PasswordInput
            label="Password"
            placeholder="Enter your password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (auth.error) auth.clearError();
            }}
          />
        </div>

        {auth.error && (
          <div className="aegis-auth-page__error" role="alert">
            {auth.error}
          </div>
        )}

        <Button
          type="submit"
          variant="primary"
          size="lg"
          fullWidth
          loading={submitting}
          disabled={!canSubmit && password.length === 0}
        >
          Sign in
        </Button>
      </form>

      <div className="aegis-auth-page__footer">
        Don&rsquo;t have an account?{" "}
        <button
          type="button"
          className="aegis-auth-page__footer-link"
          onClick={auth.goToRegister}
        >
          Sign up
        </button>
      </div>
    </div>
  );
}

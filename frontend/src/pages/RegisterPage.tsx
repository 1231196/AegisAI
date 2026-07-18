import { useMemo, useState } from "react";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { PasswordInput } from "../components/PasswordInput";
import { useAuth } from "../contexts/AuthContext";
import "./AuthPages.css";

export function RegisterPage() {
  const auth = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const confirmError = useMemo(() => {
    if (!confirm) return undefined;
    if (password.length >= 8 && confirm.length >= 8 && password !== confirm) {
      return "Passwords don\u2019t match";
    }
    return undefined;
  }, [password, confirm]);

  const canSubmit =
    email.trim().length > 0 &&
    password.length >= 8 &&
    confirm === password &&
    !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await auth.register(email.trim(), password);
    } catch {
      /* error persists via auth.error */
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="aegis-auth-page">
      <div className="aegis-auth-page__eyebrow">Create your account</div>
      <h1 className="aegis-auth-page__title">Get started with Aegis AI</h1>
      <p className="aegis-auth-page__subtitle">
        A calm, organised support workspace in under a minute.
      </p>

      <form
        onSubmit={handleSubmit}
        className="aegis-auth-page__form"
        noValidate
      >
        <div className="aegis-auth-page__form-fields">
          <Input
            type="email"
            label="Work email"
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
            placeholder="At least 8 characters"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (auth.error) auth.clearError();
            }}
            helperText={password && password.length < 8 ? "At least 8 characters" : undefined}
          />
          <PasswordInput
            label="Confirm password"
            placeholder="Re-enter your password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => {
              setConfirm(e.target.value);
              if (auth.error) auth.clearError();
            }}
            error={confirmError}
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
        >
          Create account
        </Button>
      </form>

      <div className="aegis-auth-page__footer">
        Already have an account?{" "}
        <button
          type="button"
          className="aegis-auth-page__footer-link"
          onClick={auth.goToLogin}
        >
          Sign in
        </button>
      </div>
    </div>
  );
}

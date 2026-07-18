import { useId, useState } from "react";
import type { InputHTMLAttributes } from "react";
import "./Input.css";

interface PasswordInputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  label?: string;
  error?: string;
  helperText?: string;
}

export function PasswordInput({
  label,
  error,
  helperText,
  id,
  ...rest
}: PasswordInputProps) {
  const reactId = useId();
  const inputId = id || reactId;
  const [visible, setVisible] = useState(false);

  return (
    <div className={`aegis-field ${error ? "aegis-field--error" : ""}`}>
      {label && (
        <label htmlFor={inputId} className="aegis-field__label">
          {label}
        </label>
      )}
      <div className="aegis-field__password-wrap">
        <input
          id={inputId}
          type={visible ? "text" : "password"}
          className="aegis-field__input aegis-field__input--with-suffix"
          aria-invalid={error ? "true" : undefined}
          {...rest}
        />
        <button
          type="button"
          className="aegis-field__toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          tabIndex={-1}
        >
          {visible ? <EyeOffIcon /> : <EyeIcon />}
        </button>
      </div>
      {helperText && !error && (
        <p id={`${inputId}-help`} className="aegis-field__help">
          {helperText}
        </p>
      )}
      {error && (
        <p id={`${inputId}-err`} className="aegis-field__error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function EyeIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M10 4C5 4 2 10 2 10s3 6 8 6 8-6 8-6-3-6-8-6Z" />
      <circle cx="10" cy="10" r="2.5" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 3l14 14" />
      <path d="M8.5 8.5a3 3 0 0 0 3 3" />
      <path d="M10 5c4 0 7 3 8 5-.5 1-1.2 2-2 2.7" />
      <path d="M6.2 13.6C3.7 12.4 2 10 2 10s3-6 8-6c.8 0 1.6.1 2.3.3" />
    </svg>
  );
}

import type { ButtonHTMLAttributes } from "react";
import "./Button.css";

type Variant = "primary" | "secondary" | "ghost" | "link";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  disabled,
  children,
  className,
  type = "button",
  ...rest
}: ButtonProps) {
  const cls = [
    "aegis-btn",
    `aegis-btn--${variant}`,
    `aegis-btn--${size}`,
    fullWidth ? "aegis-btn--full" : "",
    loading ? "aegis-btn--loading" : "",
    className || "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button
      type={type}
      className={cls}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <span className="aegis-btn__spinner" aria-hidden="true" />}
      <span className="aegis-btn__label">{children}</span>
    </button>
  );
}

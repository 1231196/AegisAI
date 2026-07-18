import { useId } from "react";
import type { InputHTMLAttributes } from "react";
import "./Input.css";

interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  label?: string;
  error?: string;
  helperText?: string;
  inputClassName?: string;
}

/**
 * Labelled text input. Generates a stable id via React's useId so a
 * <label htmlFor> is always wired up correctly, and surfaces error /
 * helperText below the field for screen readers (aria-describedby).
 */
export function Input({
  label,
  error,
  helperText,
  id,
  className,
  inputClassName,
  ...rest
}: InputProps) {
  const reactId = useId();
  const inputId = id || reactId;
  const describedBy = error
    ? `${inputId}-err`
    : helperText
      ? `${inputId}-help`
      : undefined;

  return (
    <div className={`aegis-field ${error ? "aegis-field--error" : ""} ${className || ""}`}>
      {label && (
        <label htmlFor={inputId} className="aegis-field__label">
          {label}
        </label>
      )}
      <input
        id={inputId}
        className={`aegis-field__input ${inputClassName || ""}`}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={describedBy}
        {...rest}
      />
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

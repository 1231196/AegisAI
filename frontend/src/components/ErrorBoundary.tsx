import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";
import "./ErrorBoundary.css";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches render-phase exceptions anywhere in the React tree and shows
 * a recoverable fallback so a single bug can't white-screen the whole
 * app. Logs the error with its component stack so it's visible in the
 * browser DevTools console (and any in-page error reporter hooked up
 * later).
 *
 * Scope: this boundary catches exceptions thrown during render, in
 * lifecycle methods, and in constructors of any descendant component.
 * It does NOT catch errors thrown inside async callbacks, ``useEffect``
 * bodies, setTimeout / event listeners, or unhandled promise
 * rejections — those need a top-level ``window.addEventListener`` or
 * similar reporter, which is out of scope for this component.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  private handleReload = () => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="aegis-error-fallback" role="alert">
          <div className="aegis-error-fallback__eyebrow">
            Something went wrong
          </div>
          <h1 className="aegis-error-fallback__title">
            We hit an unexpected error
          </h1>
          <p className="aegis-error-fallback__body">
            Your session is safe &mdash; reloading will recover the app.
          </p>
          <button
            type="button"
            className="aegis-error-fallback__button"
            onClick={this.handleReload}
          >
            Reload Aegis AI
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

import { Component, type ReactNode } from "react";
import "./ErrorBoundary.css";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error("OpenDNA UI error:", error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-card">
            <div className="error-icon">⚠</div>
            <h2>Something went wrong</h2>
            <p>The OpenDNA UI hit an unexpected error. Your session is safe.</p>
            <details>
              <summary>Technical details</summary>
              <pre>{this.state.error?.message}</pre>
              <pre>{this.state.error?.stack}</pre>
            </details>
            <div className="error-actions">
              <button className="btn-primary" onClick={this.reset}>
                Try again
              </button>
              <button
                className="btn-secondary"
                onClick={() => window.location.reload()}
              >
                Reload page
              </button>
              <a
                className="btn-secondary"
                href="https://github.com/dyber-pqc/OpenDNA/issues/new?template=bug_report.md"
                target="_blank"
                rel="noopener noreferrer"
              >
                Report bug
              </a>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

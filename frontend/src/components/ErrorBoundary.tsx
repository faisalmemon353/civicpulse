import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in component tree:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-container" data-testid="error-boundary-fallback">
          <div className="error-card">
            <div className="error-icon">⚠️</div>
            <h2>Application Error</h2>
            <p>
              An unexpected error occurred while rendering the interface.
            </p>
            {this.state.error && (
              <div className="error-details">
                <code>{this.state.error.toString()}</code>
              </div>
            )}
            <button
              id="error-boundary-retry-btn"
              className="btn btn-primary"
              onClick={this.handleReset}
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

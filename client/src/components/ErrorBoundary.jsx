import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mt-4 bg-gray-50 rounded-lg p-6 flex items-center justify-center text-center">
          <div>
            <p className="text-gray-500 text-sm font-medium">
              Something went wrong displaying this chart.
            </p>
            <p className="text-gray-400 text-xs mt-1">
              {this.props.label ?? "This section"} couldn't be rendered.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../src/components/ErrorBoundary";

const ThrowErrorComponent = () => {
  throw new Error("Simulated test rendering crash");
};

describe("ErrorBoundary Component", () => {
  it("catches render errors and renders fallback UI", () => {
    // Suppress console.error in test output for intentional error
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ThrowErrorComponent />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("error-boundary-fallback")).toBeInTheDocument();
    expect(screen.getByText("Application Error")).toBeInTheDocument();
    expect(screen.getByText(/Simulated test rendering crash/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Reload Application/i })).toBeInTheDocument();

    spy.mockRestore();
  });
});

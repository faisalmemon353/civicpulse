import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SubmitPage } from "../src/pages/SubmitPage";
import { api } from "../src/api/client";
import { ApiError } from "../src/api/types";

vi.mock("../src/api/client", () => ({
  api: {
    createComplaint: vi.fn(),
  },
}));

describe("SubmitPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("validates input length constraints client-side before submission", async () => {
    render(<SubmitPage />);

    const submitBtn = screen.getByRole("button", { name: /Submit & Triage/i });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Complaint description is required/i)).toBeInTheDocument();
    expect(screen.getByText(/Location is required/i)).toBeInTheDocument();
    expect(api.createComplaint).not.toHaveBeenCalled();

    // Test minimum character limits (< 10 chars for text, < 3 chars for location)
    const textInput = screen.getByLabelText(/Complaint Description/i);
    const locInput = screen.getByLabelText(/Incident Location/i);

    fireEvent.change(textInput, { target: { value: "Short" } });
    fireEvent.change(locInput, { target: { value: "St" } });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Complaint must be at least 10 characters/i)).toBeInTheDocument();
    expect(screen.getByText(/Location must be at least 3 characters/i)).toBeInTheDocument();
    expect(api.createComplaint).not.toHaveBeenCalled();
  });

  it("displays triage outcome results upon successful submission", async () => {
    vi.mocked(api.createComplaint).mockResolvedValueOnce({
      id: "7b4c6e93-9c8e-4a61-8ef7-47b22a014902",
      text: "Water line broken on 4th street flooding entire intersection",
      location: "4th Street & Main Ave",
      reporter_contact: "citizen@example.gov",
      category: "water",
      priority: "high",
      status: "open",
      ai_summary: "Severe water main burst flooding street and disrupting traffic.",
      triaged_by: "llm:openrouter",
      triage_latency_ms: 1250,
      created_at: "2026-09-27T00:00:00Z",
      updated_at: "2026-09-27T00:00:00Z",
    });

    render(<SubmitPage />);

    fireEvent.change(screen.getByLabelText(/Complaint Description/i), {
      target: { value: "Water line broken on 4th street flooding entire intersection" },
    });
    fireEvent.change(screen.getByLabelText(/Incident Location/i), {
      target: { value: "4th Street & Main Ave" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Submit & Triage/i }));

    expect(await screen.findByTestId("triage-result")).toBeInTheDocument();
    expect(screen.getByText(/Complaint Triaged & Logged/i)).toBeInTheDocument();
    expect(screen.getByText("water")).toBeInTheDocument();
    expect(screen.getByText("HIGH")).toBeInTheDocument();
    expect(screen.getByText("llm:openrouter")).toBeInTheDocument();
    expect(screen.getByText(/1250 ms/i)).toBeInTheDocument();
    expect(
      screen.getByText(/"Severe water main burst flooding street and disrupting traffic."/i)
    ).toBeInTheDocument();
  });

  it("handles 429 Rate Limit with Retry-After header countdown", async () => {
    const error429 = new ApiError(
      429,
      "Rate limit exceeded: 5 complaints per 60 seconds",
      15
    );
    vi.mocked(api.createComplaint).mockRejectedValueOnce(error429);

    render(<SubmitPage />);

    fireEvent.change(screen.getByLabelText(/Complaint Description/i), {
      target: { value: "A valid complaint text that exceeds ten chars" },
    });
    fireEvent.change(screen.getByLabelText(/Incident Location/i), {
      target: { value: "Central Plaza" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Submit & Triage/i }));

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/Rate Limited \(HTTP 429\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Rate limit exceeded: Token bucket exhausted/i)).toBeInTheDocument();
    expect(screen.getByText(/Cooldown timer:/i)).toBeInTheDocument();

    // Verify submit button is disabled during countdown with countdown text
    const submitBtn = screen.getByRole("button", { name: /Rate Limited/i });
    expect(submitBtn).toBeDisabled();
    expect(submitBtn).toHaveTextContent("15s");
  });
});

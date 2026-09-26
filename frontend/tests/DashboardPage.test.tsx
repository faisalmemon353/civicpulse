import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DashboardPage } from "../src/pages/DashboardPage";
import { api } from "../src/api/client";
import { ApiError, ComplaintOut } from "../src/api/types";

vi.mock("../src/api/client", () => ({
  api: {
    listComplaints: vi.fn(),
    updateComplaintStatus: vi.fn(),
  },
}));

const mockComplaint: ComplaintOut = {
  id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  text: "Streetlight outage on Elm St",
  location: "Elm St & 5th Ave",
  reporter_contact: "reporter@example.com",
  category: "streetlights",
  priority: "normal",
  status: "open",
  ai_summary: "Dark intersection due to failed lamp fixture.",
  triaged_by: "rules",
  triage_latency_ms: 15,
  created_at: "2026-09-27T00:00:00Z",
  updated_at: "2026-09-27T00:00:00Z",
};

describe("DashboardPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders list of complaints from API", async () => {
    vi.mocked(api.listComplaints).mockResolvedValueOnce({
      items: [mockComplaint],
      total: 1,
      page: 1,
      page_size: 10,
    });

    render(<DashboardPage />);

    expect(await screen.findByText(/Streetlight outage on Elm St/i)).toBeInTheDocument();
    expect(screen.getByText(/Elm St & 5th Ave/i)).toBeInTheDocument();
    expect(screen.getByText("NORMAL")).toBeInTheDocument();
    expect(screen.getByText("rules")).toBeInTheDocument();
    expect(screen.getByText("Start Progress")).toBeInTheDocument();
  });

  it("advances complaint status successfully via PATCH", async () => {
    vi.mocked(api.listComplaints).mockResolvedValueOnce({
      items: [mockComplaint],
      total: 1,
      page: 1,
      page_size: 10,
    });

    const updatedComplaint: ComplaintOut = {
      ...mockComplaint,
      status: "in_progress",
    };
    vi.mocked(api.updateComplaintStatus).mockResolvedValueOnce(updatedComplaint);

    render(<DashboardPage />);

    const progressBtn = await screen.findByText("Start Progress");
    fireEvent.click(progressBtn);

    expect(api.updateComplaintStatus).toHaveBeenCalledWith(mockComplaint.id, "in_progress");
    expect(await screen.findByText(/Complaint status updated to 'in_progress'/i)).toBeInTheDocument();
  });

  it("displays server error verbatim when status transition returns 409 Conflict", async () => {
    vi.mocked(api.listComplaints).mockResolvedValueOnce({
      items: [{ ...mockComplaint, status: "resolved" }],
      total: 1,
      page: 1,
      page_size: 10,
    });

    const conflictErr = new ApiError(
      409,
      "Cannot transition from 'resolved' to 'in_progress'"
    );
    vi.mocked(api.updateComplaintStatus).mockRejectedValueOnce(conflictErr);

    render(<DashboardPage />);

    const testConflictBtn = await screen.findByTitle(/Click to verify server returns 409/i);
    fireEvent.click(testConflictBtn);

    const banner = await screen.findByTestId("status-conflict-banner");
    expect(banner).toBeInTheDocument();
    expect(screen.getByTestId("conflict-detail")).toHaveTextContent(
      "Cannot transition from 'resolved' to 'in_progress'"
    );
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatsPage } from "../src/pages/StatsPage";
import { api } from "../src/api/client";
import { StatsWithCache } from "../src/api/types";

vi.mock("../src/api/client", () => ({
  api: {
    getStats: vi.fn(),
    getProvidersMeta: vi.fn(),
  },
}));

const mockStatsData: StatsWithCache = {
  data: {
    total: 32,
    by_category: {
      water: 8,
      electricity: 7,
      sanitation: 5,
      roads: 6,
      streetlights: 4,
      other: 2,
    },
    by_priority: {
      high: 10,
      normal: 16,
      low: 6,
    },
    by_status: {
      open: 14,
      in_progress: 10,
      resolved: 6,
      rejected: 2,
    },
  },
  cacheStatus: "HIT",
  fetchedAt: "12:00:00 PM",
};

describe("StatsPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders X-Cache: HIT badge when served from Redis cache", async () => {
    vi.mocked(api.getStats).mockResolvedValueOnce({
      ...mockStatsData,
      cacheStatus: "HIT",
    });
    vi.mocked(api.getProvidersMeta).mockResolvedValueOnce({
      active_provider: "simulated",
      recent_outcomes: [],
    });

    render(<StatsPage />);

    expect(await screen.findByTestId("cache-status-card")).toBeInTheDocument();
    const cacheBadge = screen.getByTestId("x-cache-badge");
    expect(cacheBadge).toHaveClass("x-cache-hit");
    expect(screen.getByTestId("x-cache-value")).toHaveTextContent("HIT");
    expect(screen.getByText(/Served directly from Redis in-memory cache/i)).toBeInTheDocument();
    expect(screen.getByText("32")).toBeInTheDocument();
  });

  it("renders X-Cache: MISS badge when cache is invalidated or expired", async () => {
    vi.mocked(api.getStats).mockResolvedValueOnce({
      ...mockStatsData,
      cacheStatus: "MISS",
    });
    vi.mocked(api.getProvidersMeta).mockResolvedValueOnce({
      active_provider: "llm:openrouter",
      recent_outcomes: [
        {
          provider: "llm:openrouter",
          latency_ms: 1420,
          is_fallback: false,
          recorded_at: "2026-09-27T00:00:00Z",
        },
      ],
    });

    render(<StatsPage />);

    expect(await screen.findByTestId("cache-status-card")).toBeInTheDocument();
    const cacheBadge = screen.getByTestId("x-cache-badge");
    expect(cacheBadge).toHaveClass("x-cache-miss");
    expect(screen.getByTestId("x-cache-value")).toHaveTextContent("MISS");
    expect(screen.getByText(/Aggregates queried directly from PostgreSQL/i)).toBeInTheDocument();
    
    // Check provider telemetry rendered
    const providerMatches = screen.getAllByText("llm:openrouter");
    expect(providerMatches.length).toBeGreaterThanOrEqual(1);
  });
});

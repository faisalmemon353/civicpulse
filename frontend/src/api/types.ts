export type Category =
  | "water"
  | "electricity"
  | "sanitation"
  | "roads"
  | "streetlights"
  | "other";

export type Priority = "high" | "normal" | "low";

export type Status = "open" | "in_progress" | "resolved" | "rejected";

export interface ComplaintCreate {
  text: string;
  location: string;
  reporter_contact?: string | null;
}

export interface ComplaintOut {
  id: string;
  text: string;
  location: string;
  reporter_contact: string | null;
  category: Category;
  priority: Priority;
  status: Status;
  ai_summary: string | null;
  triaged_by: string;
  triage_latency_ms: number;
  created_at: string;
  updated_at: string;
}

export interface ComplaintListResponse {
  items: ComplaintOut[];
  total: number;
  page: number;
  page_size: number;
}

export interface StatusUpdate {
  status: Status;
}

export interface StatsResponse {
  total: number;
  by_category: Record<Category, number>;
  by_priority: Record<Priority, number>;
  by_status: Record<Status, number>;
}

export interface StatsWithCache {
  data: StatsResponse;
  cacheStatus: "HIT" | "MISS" | "UNKNOWN";
  fetchedAt: string;
}

export interface ProviderOutcome {
  provider: string;
  latency_ms: number;
  is_fallback: boolean;
  recorded_at: string;
}

export interface ProvidersMetaResponse {
  active_provider: string;
  recent_outcomes: ProviderOutcome[];
}

export interface HealthCheckResponse {
  status: string;
  checks?: {
    database: boolean;
    cache: boolean;
  };
  failed?: string;
}

export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export class ApiError extends Error {
  statusCode: number;
  detail: string | ValidationErrorItem[];
  retryAfterSeconds?: number;

  constructor(
    statusCode: number,
    detail: string | ValidationErrorItem[],
    retryAfterSeconds?: number
  ) {
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
        ? detail.map((d) => `${d.loc.join(".")}: ${d.msg}`).join("; ")
        : "An API error occurred";
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.detail = detail;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

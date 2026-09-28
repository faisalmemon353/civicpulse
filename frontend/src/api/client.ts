import {
  ApiError,
  Category,
  ComplaintCreate,
  ComplaintListResponse,
  ComplaintOut,
  Priority,
  ProvidersMetaResponse,
  StatsWithCache,
  Status,
  ValidationErrorItem,
} from "./types";

const BASE_URL = "";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail: string | ValidationErrorItem[] = "An unexpected error occurred.";
    let retryAfterSeconds: number | undefined;

    const retryHeader = res.headers.get("Retry-After");
    if (retryHeader) {
      const parsed = parseInt(retryHeader, 10);
      if (!isNaN(parsed)) {
        retryAfterSeconds = parsed;
      }
    }

    try {
      const text = await res.text();
      try {
        const json = JSON.parse(text);
        if (json && json.detail !== undefined) {
          errorDetail = json.detail;
        } else {
          errorDetail = text || res.statusText || errorDetail;
        }
      } catch {
        errorDetail = text || res.statusText || errorDetail;
      }
    } catch {
      errorDetail = res.statusText || errorDetail;
    }

    throw new ApiError(res.status, errorDetail, retryAfterSeconds);
  }

  return res.json() as Promise<T>;
}

export const api = {
  async createComplaint(payload: ComplaintCreate): Promise<ComplaintOut> {
    const res = await fetch(`${BASE_URL}/api/complaints`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<ComplaintOut>(res);
  },

  async listComplaints(params?: {
    category?: Category;
    priority?: Priority;
    status?: Status;
    page?: number;
    page_size?: number;
  }): Promise<ComplaintListResponse> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.priority) query.set("priority", params.priority);
    if (params?.status) query.set("status", params.status);
    if (params?.page) query.set("page", params.page.toString());
    if (params?.page_size) query.set("page_size", params.page_size.toString());

    const url = `${BASE_URL}/api/complaints${query.toString() ? `?${query.toString()}` : ""}`;
    const res = await fetch(url);
    return handleResponse<ComplaintListResponse>(res);
  },

  async getComplaint(id: string): Promise<ComplaintOut> {
    const res = await fetch(`${BASE_URL}/api/complaints/${id}`);
    return handleResponse<ComplaintOut>(res);
  },

  async updateComplaintStatus(id: string, newStatus: Status): Promise<ComplaintOut> {
    const res = await fetch(`${BASE_URL}/api/complaints/${id}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status: newStatus }),
    });
    return handleResponse<ComplaintOut>(res);
  },

  async getStats(): Promise<StatsWithCache> {
    const res = await fetch(`${BASE_URL}/api/stats`);
    const xCacheHeader = res.headers.get("X-Cache")?.toUpperCase();
    const cacheStatus: "HIT" | "MISS" | "UNKNOWN" =
      xCacheHeader === "HIT" ? "HIT" : xCacheHeader === "MISS" ? "MISS" : "UNKNOWN";

    const data = await handleResponse<StatsWithCache["data"]>(res);
    return {
      data,
      cacheStatus,
      fetchedAt: new Date().toLocaleTimeString(),
    };
  },

  async getProvidersMeta(): Promise<ProvidersMetaResponse> {
    const res = await fetch(`${BASE_URL}/api/meta/providers`);
    return handleResponse<ProvidersMetaResponse>(res);
  },

  async getHealth(): Promise<{ status: string }> {
    const res = await fetch(`${BASE_URL}/health`);
    return handleResponse<{ status: string }>(res);
  },

  async getReady(): Promise<{ status: string; checks?: { database: boolean; cache: boolean }; failed?: string }> {
    const res = await fetch(`${BASE_URL}/ready`);
    return handleResponse<{ status: string; checks?: { database: boolean; cache: boolean }; failed?: string }>(res);
  },
};

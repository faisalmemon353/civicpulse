import React, { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import {
  ApiError,
  Category,
  ComplaintOut,
  Priority,
  Status,
} from "../api/types";

export const DashboardPage: React.FC = () => {
  const [complaints, setComplaints] = useState<ComplaintOut[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<Category | "">("");
  const [priorityFilter, setPriorityFilter] = useState<Priority | "">("");
  const [statusFilter, setStatusFilter] = useState<Status | "">("");
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Status update tracking
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [conflictError, setConflictError] = useState<{ id: string; message: string } | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchComplaints = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await api.listComplaints({
        category: categoryFilter || undefined,
        priority: priorityFilter || undefined,
        status: statusFilter || undefined,
        page,
        page_size: pageSize,
      });
      setComplaints(response.items);
      setTotalCount(response.total);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(typeof err.detail === "string" ? err.detail : err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to load complaints.");
      }
    } finally {
      setIsLoading(false);
    }
  }, [categoryFilter, priorityFilter, statusFilter, page, pageSize]);

  useEffect(() => {
    fetchComplaints();
  }, [fetchComplaints]);

  const handleStatusTransition = async (complaintId: string, nextStatus: Status) => {
    setUpdatingId(complaintId);
    setConflictError(null);
    setActionSuccess(null);

    try {
      const updated = await api.updateComplaintStatus(complaintId, nextStatus);
      // Update local state
      setComplaints((prev) =>
        prev.map((c) => (c.id === complaintId ? updated : c))
      );
      setActionSuccess(`Complaint status updated to '${nextStatus}'.`);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        // Specifically show the verbatim 409 conflict message
        const msg = typeof err.detail === "string" ? err.detail : err.message;
        setConflictError({ id: complaintId, message: msg });
      } else if (err instanceof Error) {
        setConflictError({ id: complaintId, message: err.message });
      } else {
        setConflictError({ id: complaintId, message: "Transition failed." });
      }
    } finally {
      setUpdatingId(null);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  const getPriorityBadgeClass = (p: Priority) => {
    switch (p) {
      case "high":
        return "priority-high";
      case "normal":
        return "priority-normal";
      case "low":
        return "priority-low";
    }
  };

  const getStatusBadgeClass = (s: Status) => {
    switch (s) {
      case "open":
        return "status-open";
      case "in_progress":
        return "status-in-progress";
      case "resolved":
        return "status-resolved";
      case "rejected":
        return "status-rejected";
    }
  };

  return (
    <div className="dashboard-page-container">
      <div className="page-header">
        <div className="header-text-group">
          <h1 className="page-title">Complaint Triage Dashboard</h1>
          <p className="page-description">
            Monitor, inspect, and advance municipal complaints across departments and workflow stages.
          </p>
        </div>
        <div className="header-stats-pill">
          Total Complaints: <strong>{totalCount}</strong>
        </div>
      </div>

      {actionSuccess && (
        <div className="alert-banner alert-success animate-fade-in" role="status">
          <span className="alert-icon">✓</span>
          <div className="alert-content">
            <p>{actionSuccess}</p>
          </div>
        </div>
      )}

      {conflictError && (
        <div
          id="status-conflict-banner"
          className="alert-banner alert-conflict animate-fade-in"
          role="alert"
          data-testid="status-conflict-banner"
        >
          <span className="alert-icon">🚫</span>
          <div className="alert-content">
            <h4>Workflow Transition Conflict (HTTP 409)</h4>
            <p className="verbatim-message" data-testid="conflict-detail">
              {conflictError.message}
            </p>
          </div>
          <button
            className="alert-dismiss-btn"
            onClick={() => setConflictError(null)}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="alert-banner alert-error" role="alert">
          <span className="alert-icon">⚠️</span>
          <div className="alert-content">
            <h4>Error Loading Complaints</h4>
            <p>{errorMessage}</p>
          </div>
          <button className="btn btn-sm btn-secondary" onClick={() => fetchComplaints()}>
            Retry
          </button>
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="filters-toolbar glass-card">
        <div className="filter-group">
          <label htmlFor="filter-category">Category</label>
          <select
            id="filter-category"
            className="filter-select"
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value as Category | "");
              setPage(1);
            }}
          >
            <option value="">All Categories</option>
            <option value="water">Water</option>
            <option value="electricity">Electricity</option>
            <option value="sanitation">Sanitation</option>
            <option value="roads">Roads</option>
            <option value="streetlights">Streetlights</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-priority">Priority</label>
          <select
            id="filter-priority"
            className="filter-select"
            value={priorityFilter}
            onChange={(e) => {
              setPriorityFilter(e.target.value as Priority | "");
              setPage(1);
            }}
          >
            <option value="">All Priorities</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-status">Status</label>
          <select
            id="filter-status"
            className="filter-select"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as Status | "");
              setPage(1);
            }}
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="resolved">Resolved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="filter-pagesize">Page Size</label>
          <select
            id="filter-pagesize"
            className="filter-select"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>

        <div className="filter-actions">
          <button
            id="refresh-complaints-btn"
            className="btn btn-secondary btn-icon"
            onClick={() => fetchComplaints()}
            title="Refresh List"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Complaints List / Table */}
      {isLoading ? (
        <div className="loading-card glass-card" data-testid="dashboard-loading">
          <div className="loading-spinner-ring" />
          <p>Loading complaints from database...</p>
        </div>
      ) : complaints.length === 0 ? (
        <div className="empty-state-card glass-card" data-testid="dashboard-empty">
          <div className="empty-icon">📋</div>
          <h3>No Complaints Match Your Filters</h3>
          <p>Try resetting filters or submit a new complaint to test triage.</p>
        </div>
      ) : (
        <div className="complaints-table-container glass-card">
          <table className="complaints-table" data-testid="complaints-table">
            <thead>
              <tr>
                <th>Complaint Details</th>
                <th>Category</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Triage Engine</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {complaints.map((item) => (
                <tr key={item.id} className="complaint-row" data-testid={`complaint-row-${item.id}`}>
                  <td className="col-details">
                    <p className="complaint-text">{item.text}</p>
                    <div className="complaint-meta-line">
                      <span className="location-pin">
                        📍 {item.location}
                      </span>
                      {item.reporter_contact && (
                        <span className="reporter-contact">
                          👤 {item.reporter_contact}
                        </span>
                      )}
                      <span className="timestamp">
                        🕒 {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    {item.ai_summary && (
                      <div className="complaint-ai-summary">
                        <strong>AI Summary:</strong> {item.ai_summary}
                      </div>
                    )}
                  </td>

                  <td className="col-category">
                    <span className={`category-tag category-${item.category}`}>
                      {item.category}
                    </span>
                  </td>

                  <td className="col-priority">
                    <span className={`priority-tag ${getPriorityBadgeClass(item.priority)}`}>
                      {item.priority.toUpperCase()}
                    </span>
                  </td>

                  <td className="col-status">
                    <span className={`status-badge ${getStatusBadgeClass(item.status)}`}>
                      {item.status.replace("_", " ")}
                    </span>
                  </td>

                  <td className="col-triage">
                    <div className="triage-info-stack">
                      <span className="triage-engine-name">{item.triaged_by}</span>
                      <span className="triage-engine-latency">{item.triage_latency_ms} ms</span>
                    </div>
                  </td>

                  <td className="col-actions">
                    <div className="action-buttons-group">
                      {item.status === "open" && (
                        <>
                          <button
                            id={`action-progress-${item.id}`}
                            className="btn btn-xs btn-primary"
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusTransition(item.id, "in_progress")}
                          >
                            {updatingId === item.id ? "Updating..." : "Start Progress"}
                          </button>
                          <button
                            id={`action-reject-${item.id}`}
                            className="btn btn-xs btn-danger-outline"
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusTransition(item.id, "rejected")}
                          >
                            Reject
                          </button>
                        </>
                      )}

                      {item.status === "in_progress" && (
                        <>
                          <button
                            id={`action-resolve-${item.id}`}
                            className="btn btn-xs btn-success"
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusTransition(item.id, "resolved")}
                          >
                            {updatingId === item.id ? "Updating..." : "Resolve"}
                          </button>
                          <button
                            id={`action-reject-${item.id}`}
                            className="btn btn-xs btn-danger-outline"
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusTransition(item.id, "rejected")}
                          >
                            Reject
                          </button>
                        </>
                      )}

                      {(item.status === "resolved" || item.status === "rejected") && (
                        <div className="terminal-status-indicator">
                          <span className="terminal-checkmark">✓</span> Finalized
                          {/* Test helper button to deliberately test 409 transition in UI */}
                          <button
                            id={`test-conflict-${item.id}`}
                            className="test-conflict-btn"
                            title="Click to verify server returns 409 on invalid transition"
                            disabled={updatingId === item.id}
                            onClick={() => handleStatusTransition(item.id, "in_progress")}
                          >
                            Test 409
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination Toolbar */}
          <div className="pagination-bar">
            <div className="pagination-info">
              Showing page <strong>{page}</strong> of <strong>{totalPages}</strong> ({totalCount} total)
            </div>
            <div className="pagination-controls">
              <button
                id="pagination-prev-btn"
                className="btn btn-sm btn-secondary"
                disabled={page <= 1 || isLoading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                ← Previous
              </button>
              <span className="page-number-display">{page}</span>
              <button
                id="pagination-next-btn"
                className="btn btn-sm btn-secondary"
                disabled={page >= totalPages || isLoading}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

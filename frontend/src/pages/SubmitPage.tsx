import React, { useState, useEffect, useRef } from "react";
import { api } from "../api/client";
import { ApiError, ComplaintOut } from "../api/types";

interface SubmitPageProps {
  onNavigateToDashboard?: () => void;
}

export const SubmitPage: React.FC<SubmitPageProps> = ({ onNavigateToDashboard }) => {
  const [text, setText] = useState("");
  const [location, setLocation] = useState("");
  const [reporterContact, setReporterContact] = useState("");

  // Validation
  const [errors, setErrors] = useState<{ text?: string; location?: string; contact?: string }>({});

  // Submission state
  const [isLoading, setIsLoading] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const timerRef = useRef<number | null>(null);

  // Result & Error state
  const [submittedComplaint, setSubmittedComplaint] = useState<ComplaintOut | null>(null);
  const [apiErrorMessage, setApiErrorMessage] = useState<string | null>(null);

  // 429 Rate limiting state
  const [rateLimitCountdown, setRateLimitCountdown] = useState<number | null>(null);
  const countdownIntervalRef = useRef<number | null>(null);

  // Elapsed time tracker during loading
  useEffect(() => {
    if (isLoading) {
      setElapsedTime(0);
      const start = Date.now();
      timerRef.current = window.setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - start) / 100) / 10);
      }, 100);
    } else {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
      }
    };
  }, [isLoading]);

  // Rate limit countdown timer
  useEffect(() => {
    if (rateLimitCountdown !== null && rateLimitCountdown > 0) {
      countdownIntervalRef.current = window.setInterval(() => {
        setRateLimitCountdown((prev) => {
          if (prev === null || prev <= 1) {
            clearInterval(countdownIntervalRef.current!);
            return null;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => {
      if (countdownIntervalRef.current !== null) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, [rateLimitCountdown]);

  const validate = (): boolean => {
    const newErrors: { text?: string; location?: string; contact?: string } = {};

    const trimmedText = text.trim();
    if (!trimmedText) {
      newErrors.text = "Complaint description is required.";
    } else if (trimmedText.length < 10) {
      newErrors.text = `Complaint must be at least 10 characters (currently ${trimmedText.length}).`;
    } else if (trimmedText.length > 2000) {
      newErrors.text = `Complaint cannot exceed 2000 characters (currently ${trimmedText.length}).`;
    }

    const trimmedLoc = location.trim();
    if (!trimmedLoc) {
      newErrors.location = "Location is required.";
    } else if (trimmedLoc.length < 3) {
      newErrors.location = `Location must be at least 3 characters (currently ${trimmedLoc.length}).`;
    } else if (trimmedLoc.length > 200) {
      newErrors.location = `Location cannot exceed 200 characters (currently ${trimmedLoc.length}).`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiErrorMessage(null);
    setSubmittedComplaint(null);

    if (rateLimitCountdown !== null && rateLimitCountdown > 0) {
      return;
    }

    if (!validate()) {
      return;
    }

    setIsLoading(true);

    try {
      const complaint = await api.createComplaint({
        text: text.trim(),
        location: location.trim(),
        reporter_contact: reporterContact.trim() || undefined,
      });
      setSubmittedComplaint(complaint);
      setText("");
      setLocation("");
      setReporterContact("");
      setErrors({});
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.statusCode === 429) {
          const waitTime = err.retryAfterSeconds || 10;
          setRateLimitCountdown(waitTime);
          setApiErrorMessage(
            `Rate limit exceeded: Token bucket exhausted. Please wait ${waitTime} seconds before submitting again.`
          );
        } else if (err.statusCode === 400 && Array.isArray(err.detail)) {
          const fieldErrors: { text?: string; location?: string; contact?: string } = {};
          err.detail.forEach((item) => {
            const field = item.loc[item.loc.length - 1];
            if (field === "text") fieldErrors.text = item.msg;
            if (field === "location") fieldErrors.location = item.msg;
            if (field === "reporter_contact") fieldErrors.contact = item.msg;
          });
          setErrors(fieldErrors);
          setApiErrorMessage("Validation failed. Please review the errors below.");
        } else {
          setApiErrorMessage(typeof err.detail === "string" ? err.detail : err.message);
        }
      } else if (err instanceof Error) {
        setApiErrorMessage(err.message);
      } else {
        setApiErrorMessage("An unknown error occurred.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const getTriagedByBadgeClass = (triagedBy: string) => {
    if (triagedBy.includes("fallback")) return "badge-fallback";
    if (triagedBy.startsWith("llm:")) return "badge-llm";
    if (triagedBy === "rules") return "badge-rules";
    return "badge-simulated";
  };

  return (
    <div className="submit-page-container">
      <div className="page-header">
        <h1 className="page-title">Submit Citizen Complaint</h1>
        <p className="page-description">
          Describe the municipal incident or infrastructure failure. Our automated AI triage engine
          will instantly categorize the issue, assign operational priority, and generate an executive summary.
        </p>
      </div>

      {apiErrorMessage && (
        <div
          id="submit-error-banner"
          className={`alert-banner ${rateLimitCountdown !== null ? "alert-rate-limit" : "alert-error"}`}
          role="alert"
        >
          <div className="alert-icon">
            {rateLimitCountdown !== null ? "⏳" : "⚠️"}
          </div>
          <div className="alert-content">
            <h4>{rateLimitCountdown !== null ? "Rate Limited (HTTP 429)" : "Submission Failed"}</h4>
            <p>{apiErrorMessage}</p>
            {rateLimitCountdown !== null && (
              <div className="rate-limit-timer">
                Cooldown timer: <strong>{rateLimitCountdown}s</strong> remaining
              </div>
            )}
          </div>
        </div>
      )}

      {submittedComplaint && (
        <div id="triage-result-card" className="triage-result-card animate-fade-in" data-testid="triage-result">
          <div className="result-card-header">
            <div className="success-badge">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
              Complaint Triaged & Logged
            </div>
            <span className="complaint-id" title={submittedComplaint.id}>
              ID: {submittedComplaint.id.slice(0, 8)}...
            </span>
          </div>

          <div className="result-grid">
            <div className="result-metric">
              <span className="metric-label">Category</span>
              <span className={`category-tag category-${submittedComplaint.category}`}>
                {submittedComplaint.category}
              </span>
            </div>

            <div className="result-metric">
              <span className="metric-label">Priority</span>
              <span className={`priority-tag priority-${submittedComplaint.priority}`}>
                {submittedComplaint.priority.toUpperCase()}
              </span>
            </div>

            <div className="result-metric">
              <span className="metric-label">Triage Engine</span>
              <span className={`triaged-by-tag ${getTriagedByBadgeClass(submittedComplaint.triaged_by)}`}>
                {submittedComplaint.triaged_by}
              </span>
            </div>

            <div className="result-metric">
              <span className="metric-label">Triage Latency</span>
              <span className="latency-val">
                {submittedComplaint.triage_latency_ms} ms
              </span>
            </div>
          </div>

          {submittedComplaint.ai_summary && (
            <div className="ai-summary-box">
              <span className="summary-title">AI Executive Summary</span>
              <p className="summary-text">"{submittedComplaint.ai_summary}"</p>
            </div>
          )}

          <div className="result-actions">
            <button
              id="submit-another-btn"
              className="btn btn-secondary"
              onClick={() => setSubmittedComplaint(null)}
            >
              Submit Another Complaint
            </button>
            {onNavigateToDashboard && (
              <button
                id="view-in-dashboard-btn"
                className="btn btn-primary"
                onClick={onNavigateToDashboard}
              >
                View in Triage Dashboard
              </button>
            )}
          </div>
        </div>
      )}

      <form id="complaint-form" className="complaint-form glass-card" onSubmit={handleSubmit} noValidate>
        <div className="form-group">
          <div className="label-row">
            <label htmlFor="complaint-text">
              Complaint Description <span className="required-star">*</span>
            </label>
            <span
              className={`char-counter ${
                text.trim().length > 2000 || (text.trim().length > 0 && text.trim().length < 10)
                  ? "counter-warning"
                  : ""
              }`}
            >
              {text.trim().length}/2000 chars (min 10)
            </span>
          </div>
          <textarea
            id="complaint-text"
            rows={5}
            placeholder="Provide specific details about the issue (e.g. Main water line rupture flooding 4th Street, water pressure dropped completely)..."
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (errors.text) setErrors((prev) => ({ ...prev, text: undefined }));
            }}
            disabled={isLoading || (rateLimitCountdown !== null && rateLimitCountdown > 0)}
            className={`form-control ${errors.text ? "is-invalid" : ""}`}
            required
          />
          {errors.text && <div className="field-error-msg">{errors.text}</div>}
        </div>

        <div className="form-row">
          <div className="form-group flex-2">
            <div className="label-row">
              <label htmlFor="complaint-location">
                Incident Location <span className="required-star">*</span>
              </label>
              <span
                className={`char-counter ${
                  location.trim().length > 200 || (location.trim().length > 0 && location.trim().length < 3)
                    ? "counter-warning"
                    : ""
                }`}
              >
                {location.trim().length}/200 chars (min 3)
              </span>
            </div>
            <input
              type="text"
              id="complaint-location"
              placeholder="e.g., Corner of 4th St and Elm Ave, Sector 7"
              value={location}
              onChange={(e) => {
                setLocation(e.target.value);
                if (errors.location) setErrors((prev) => ({ ...prev, location: undefined }));
              }}
              disabled={isLoading || (rateLimitCountdown !== null && rateLimitCountdown > 0)}
              className={`form-control ${errors.location ? "is-invalid" : ""}`}
              required
            />
            {errors.location && <div className="field-error-msg">{errors.location}</div>}
          </div>

          <div className="form-group flex-1">
            <div className="label-row">
              <label htmlFor="complaint-contact">
                Reporter Contact <span className="optional-label">(Optional)</span>
              </label>
            </div>
            <input
              type="text"
              id="complaint-contact"
              placeholder="Email or Phone"
              value={reporterContact}
              onChange={(e) => setReporterContact(e.target.value)}
              disabled={isLoading || (rateLimitCountdown !== null && rateLimitCountdown > 0)}
              className="form-control"
            />
          </div>
        </div>

        <div className="form-footer">
          {isLoading ? (
            <div className="honest-loading-state" data-testid="honest-loading">
              <div className="loading-spinner-ring" />
              <div className="loading-text-stack">
                <span className="loading-primary">
                  Running Automated Triage Pipeline...
                </span>
                <span className="loading-secondary">
                  Calling provider model • Elapsed: <strong>{elapsedTime.toFixed(1)}s</strong>
                </span>
              </div>
            </div>
          ) : (
            <button
              type="submit"
              id="submit-complaint-btn"
              className="btn btn-primary btn-large"
              disabled={rateLimitCountdown !== null && rateLimitCountdown > 0}
            >
              {rateLimitCountdown !== null && rateLimitCountdown > 0 ? (
                <>Rate Limited ({rateLimitCountdown}s)</>
              ) : (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                  Submit & Triage Complaint
                </>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
};

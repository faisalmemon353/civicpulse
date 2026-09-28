import React, { useEffect, useState } from "react";
import { api } from "../api/client";

export type NavTab = "submit" | "dashboard" | "stats";

interface NavbarProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onTabChange }) => {
  const [systemStatus, setSystemStatus] = useState<"checking" | "ready" | "degraded">("checking");
  const [statusTooltip, setStatusTooltip] = useState<string>("Checking readiness...");

  const checkHealth = async () => {
    try {
      const res = await api.getReady();
      if (res.status === "ready") {
        setSystemStatus("ready");
        setStatusTooltip("PostgreSQL + Redis Operational");
      } else {
        setSystemStatus("degraded");
        setStatusTooltip(res.failed ? `Degraded: ${res.failed}` : "Degraded");
      }
    } catch (err: unknown) {
      setSystemStatus("degraded");
      setStatusTooltip(err instanceof Error ? err.message : "Service Unavailable");
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 20000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="navbar-container">
      <div className="navbar-brand" onClick={() => onTabChange("dashboard")}>
        <div className="brand-logo-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
          <span className="pulse-dot" />
        </div>
        <div className="brand-text">
          <span className="brand-title">CivicPulse</span>
          <span className="brand-subtitle">Municipal Triage Platform</span>
        </div>
      </div>

      <nav className="navbar-links" aria-label="Main Navigation">
        <button
          id="nav-tab-submit"
          className={`nav-btn ${activeTab === "submit" ? "active" : ""}`}
          onClick={() => onTabChange("submit")}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Submit Complaint
        </button>

        <button
          id="nav-tab-dashboard"
          className={`nav-btn ${activeTab === "dashboard" ? "active" : ""}`}
          onClick={() => onTabChange("dashboard")}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" />
            <rect x="14" y="3" width="7" height="7" />
            <rect x="14" y="14" width="7" height="7" />
            <rect x="3" y="14" width="7" height="7" />
          </svg>
          Triage Dashboard
        </button>

        <button
          id="nav-tab-stats"
          className={`nav-btn ${activeTab === "stats" ? "active" : ""}`}
          onClick={() => onTabChange("stats")}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="20" x2="18" y2="10" />
            <line x1="12" y1="20" x2="12" y2="4" />
            <line x1="6" y1="20" x2="6" y2="14" />
          </svg>
          Analytics & Cache
        </button>
      </nav>

      <div className="navbar-status" title={statusTooltip}>
        <span className={`status-indicator-dot ${systemStatus}`} />
        <span className="status-indicator-text">
          {systemStatus === "ready"
            ? "API Ready"
            : systemStatus === "degraded"
            ? "Degraded"
            : "Checking..."}
        </span>
      </div>
    </header>
  );
};

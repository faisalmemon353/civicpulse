import React, { useState } from "react";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Navbar, NavTab } from "./components/Navbar";
import { SubmitPage } from "./pages/SubmitPage";
import { DashboardPage } from "./pages/DashboardPage";
import { StatsPage } from "./pages/StatsPage";
import "./App.css";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>("dashboard");

  return (
    <ErrorBoundary>
      <div className="app-layout">
        <Navbar activeTab={activeTab} onTabChange={setActiveTab} />

        <main className="main-content">
          {activeTab === "submit" && (
            <SubmitPage onNavigateToDashboard={() => setActiveTab("dashboard")} />
          )}
          {activeTab === "dashboard" && <DashboardPage />}
          {activeTab === "stats" && <StatsPage />}
        </main>

        <footer className="app-footer">
          <div className="footer-content">
            <span>
              <strong>CivicPulse</strong> — Intelligent Municipal Complaint Triage
            </span>
            <span className="footer-separator">•</span>
            <span>CS4032 Assignment</span>
            <span className="footer-separator">•</span>
            <span>FastAPI + PostgreSQL + Redis + React 18</span>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  );
};

export default App;

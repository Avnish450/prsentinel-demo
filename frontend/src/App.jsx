import React, { useState, useEffect } from "react";
import { ToastProvider, useToast } from "./components/Toast";
import { Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { OverviewPage } from "./pages/OverviewPage";
import { ReposPage } from "./pages/ReposPage";
import { JobsPage } from "./pages/JobsPage";
import { FindingsPage } from "./pages/FindingsPage";
import { FixesPage } from "./pages/FixesPage";
import { PolicyPage } from "./pages/PolicyPage";
import { AuditPage } from "./pages/AuditPage";
import { api } from "./api/client";

function DashboardContent() {
  const [currentTab, setCurrentTab] = useState("repos"); // Default landing page per specification
  const [searchQuery, setSearchQuery] = useState("");
  const [stats, setStats] = useState(null);
  const [repos, setRepos] = useState([]);
  const [reposLoading, setReposLoading] = useState(false);

  // Cross-page navigation state
  const [activeJobId, setActiveJobId] = useState(null);
  const [selectedFindingId, setSelectedFindingId] = useState(null);
  const [initialFindingsLevel, setInitialFindingsLevel] = useState("");
  const [initialFindingsRepo, setInitialFindingsRepo] = useState("");
  const [fixesTestOpen, setFixesTestOpen] = useState(false);

  const fetchStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error("Failed to load stats:", err);
    }
  };

  const fetchRepos = async () => {
    setReposLoading(true);
    try {
      const data = await api.getRepos();
      setRepos(data);
    } catch (err) {
      console.error("Failed to load repos:", err);
    } finally {
      setReposLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchRepos();
    const interval = setInterval(fetchStats, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleNavigateToJob = (jobId) => {
    setActiveJobId(jobId);
    setCurrentTab("jobs");
  };

  const handleNavigateToFindings = (repoId = "", level = "") => {
    setInitialFindingsRepo(repoId);
    setInitialFindingsLevel(level);
    setCurrentTab("findings");
  };

  const handleSelectFinding = (findingId) => {
    setSelectedFindingId(findingId);
    setCurrentTab("findings");
  };

  const handleOpenTestRule = () => {
    setFixesTestOpen(true);
    setCurrentTab("fixes");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100 font-sans">
      {/* Left Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={(tab) => {
          setCurrentTab(tab);
          if (tab !== "findings") setSelectedFindingId(null);
        }}
        stats={stats}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Header Bar */}
        <TopBar
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          onNewScan={() => setCurrentTab("repos")}
          onTestRule={handleOpenTestRule}
        />

        {/* Scrollable Page View */}
        <main className="flex-1 overflow-y-auto p-8">
          <div className="max-w-7xl mx-auto">
            {currentTab === "overview" && (
              <OverviewPage
                stats={stats}
                onNavigate={(tab, filter) => {
                  if (tab === "findings") {
                    setInitialFindingsLevel(filter || "");
                  }
                  setCurrentTab(tab);
                }}
                onSelectFinding={handleSelectFinding}
              />
            )}

            {currentTab === "repos" && (
              <ReposPage
                repos={repos}
                loading={reposLoading}
                onRefresh={() => {
                  fetchRepos();
                  fetchStats();
                }}
                onNavigateToJob={handleNavigateToJob}
                onNavigateToFindings={handleNavigateToFindings}
              />
            )}

            {currentTab === "jobs" && (
              <JobsPage
                activeJobId={activeJobId}
                onNavigateToFindings={handleNavigateToFindings}
              />
            )}

            {currentTab === "findings" && (
              <FindingsPage
                initialLevelFilter={initialFindingsLevel}
                initialRepoFilter={initialFindingsRepo}
                selectedFindingId={selectedFindingId}
                onCloseSelected={() => setSelectedFindingId(null)}
              />
            )}

            {currentTab === "fixes" && (
              <FixesPage initialTestOpen={fixesTestOpen} />
            )}

            {currentTab === "policy" && <PolicyPage />}

            {currentTab === "audit" && <AuditPage />}
          </div>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <DashboardContent />
    </ToastProvider>
  );
}


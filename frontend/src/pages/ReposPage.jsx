import React, { useState } from "react";
import {
  FolderGit2,
  GitPullRequest,
  History,
  GitCompare,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Trash2,
  ExternalLink,
  ShieldAlert,
  Lock,
  ArrowRight,
  GitBranch,
} from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

const GITHUB_REGEX = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+(\.git)?$/;

export function ReposPage({ repos, loading, onRefresh, onNavigateToJob, onNavigateToFindings }) {
  const { addToast } = useToast();

  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [scanMode, setScanMode] = useState("open_prs");
  const [submitting, setSubmitting] = useState(false);

  // Mode specific options
  const [singlePrUrl, setSinglePrUrl] = useState("");
  const [baseBranch, setBaseBranch] = useState("main");
  const [headBranch, setHeadBranch] = useState("HEAD");
  const [maxCommits, setMaxCommits] = useState(500);
  const [patchText, setPatchText] = useState("");

  // URL inline validation
  const isValidUrl = GITHUB_REGEX.test(url.trim());
  const isUrlDirty = url.trim().length > 0;

  const handleExampleClick = (exampleUrl) => {
    setUrl(exampleUrl);
    setScanMode("history_audit");
    setMaxCommits(50);
  };

  const handleAddAndScan = async (e) => {
    e.preventDefault();

    if (scanMode === "patch_upload") {
      if (!patchText.trim()) {
        addToast("Please paste diff content or drop a patch file", "warn");
        return;
      }
      setSubmitting(true);
      try {
        const job = await api.createJob({
          mode: "patch_upload",
          patch_content: patchText,
          params: { title: "Direct Patch Upload" }
        });
        addToast("Patch analysis job queued successfully!");
        onNavigateToJob(job.id);
      } catch (err) {
        addToast(err.message, "error");
      } finally {
        setSubmitting(false);
      }
      return;
    }

    if (!isValidUrl) {
      addToast("Please provide a valid GitHub repository URL (https://github.com/owner/repo)", "error");
      return;
    }

    setSubmitting(true);
    try {
      const params = {};
      if (scanMode === "single_pr") params.pr_url = singlePrUrl;
      if (scanMode === "branch_compare") {
        params.base_branch = baseBranch;
        params.head_branch = headBranch;
      }
      if (scanMode === "history_audit") params.max_commits = Number(maxCommits) || 500;

      const newRepo = await api.createRepo({
        url: url.trim(),
        token: token.trim() || undefined,
        scan_mode: scanMode,
        params,
      });

      addToast(`Repository ${newRepo.owner}/${newRepo.name} added & scan queued!`);
      setUrl("");
      setToken("");
      onRefresh();
      // Fetch newest job to navigate
      const jobs = await api.getJobs(1);
      if (jobs && jobs.length > 0) {
        onNavigateToJob(jobs[0].id);
      }
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRescan = async (repoId) => {
    try {
      const res = await api.rescanRepo(repoId, "open_prs");
      addToast("Rescan queued for repository");
      onRefresh();
      onNavigateToJob(res.job_id);
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handlePullLatest = async (repoId) => {
    try {
      const res = await api.pullRepo(repoId);
      addToast("Git pull & history scan queued");
      onRefresh();
      onNavigateToJob(res.job_id);
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleDelete = async (repoId, name) => {
    if (!confirm(`Are you sure you want to remove ${name} and its findings?`)) return;
    try {
      await api.deleteRepo(repoId);
      addToast(`Repository removed`);
      onRefresh();
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      setPatchText(evt.target?.result || "");
      setScanMode("patch_upload");
      addToast(`Loaded ${file.name} (${Math.round(file.size / 1024)} KB)`);
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Monitored Repositories</h1>
        <p className="text-sm text-slate-400 mt-1">
          Connect GitHub codebases to detect safety check reversals across PRs and git commit history.
        </p>
      </div>

      {/* Prominent "Add Repository" Card */}
      <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center gap-2.5 pb-4 border-b border-slate-800/80">
          <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            <FolderGit2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-white">Add Repository & Run Scan</h2>
            <p className="text-xs text-slate-400">Deterministic sandbox execution without running untrusted code</p>
          </div>
        </div>

        <form onSubmit={handleAddAndScan} className="mt-6 space-y-5">
          {/* URL Input */}
          {scanMode !== "patch_upload" && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                GitHub Repository URL <span className="text-rose-400">*</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://github.com/organization/repository"
                  className={`w-full bg-slate-950 border rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 transition-colors focus:outline-none focus:ring-2 ${
                    isUrlDirty && !isValidUrl
                      ? "border-rose-500/60 focus:ring-rose-500/40"
                      : isUrlDirty && isValidUrl
                      ? "border-emerald-500/60 focus:ring-emerald-500/40"
                      : "border-slate-800 focus:border-indigo-500 focus:ring-indigo-500/30"
                  }`}
                />
                {isUrlDirty && (
                  <div className="absolute right-3.5 top-1/2 -translate-y-1/2">
                    {isValidUrl ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-rose-400" />
                    )}
                  </div>
                )}
              </div>
              {isUrlDirty && !isValidUrl && (
                <p className="text-xs text-rose-400 mt-1.5 flex items-center gap-1">
                  Must strictly match format: https://github.com/owner/repository
                </p>
              )}
            </div>
          )}

          {/* Scan Mode Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">Scan Mode</label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
              {[
                { id: "open_prs", label: "Open PRs", icon: GitPullRequest, desc: "Scan active PRs" },
                { id: "single_pr", label: "Single PR URL", icon: GitPullRequest, desc: "Inspect specific PR" },
                { id: "history_audit", label: "History Audit", icon: History, desc: "Trace git blame" },
                { id: "branch_compare", label: "Branch Compare", icon: GitCompare, desc: "Diff two branches" },
                { id: "patch_upload", label: "Patch Upload", icon: UploadCloud, desc: "Raw diff scan" },
              ].map((m) => {
                const Icon = m.icon;
                const active = scanMode === m.id;
                return (
                  <button
                    type="button"
                    key={m.id}
                    onClick={() => setScanMode(m.id)}
                    className={`p-3 rounded-xl border text-left flex flex-col gap-1 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                      active
                        ? "bg-indigo-600/15 border-indigo-500 text-white shadow-sm"
                        : "bg-slate-950/60 border-slate-800 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                    }`}
                  >
                    <div className="flex items-center gap-1.5">
                      <Icon className={`w-3.5 h-3.5 ${active ? "text-indigo-400" : "text-slate-500"}`} />
                      <span className="text-xs font-semibold">{m.label}</span>
                    </div>
                    <span className="text-[10px] text-slate-500">{m.desc}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Conditional Mode Inputs */}
          {scanMode === "single_pr" && (
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Single Pull Request URL <span className="text-rose-400">*</span>
              </label>
              <input
                type="text"
                value={singlePrUrl}
                onChange={(e) => setSinglePrUrl(e.target.value)}
                placeholder="https://github.com/owner/repository/pull/123"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          {scanMode === "branch_compare" && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Base Branch</label>
                <input
                  type="text"
                  value={baseBranch}
                  onChange={(e) => setBaseBranch(e.target.value)}
                  placeholder="main"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">Head Branch / Ref</label>
                <input
                  type="text"
                  value={headBranch}
                  onChange={(e) => setHeadBranch(e.target.value)}
                  placeholder="feature-branch"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100"
                />
              </div>
            </div>
          )}

          {scanMode === "history_audit" && (
            <div className="max-w-xs">
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Audit Depth (Commits to inspect)
              </label>
              <input
                type="number"
                min="10"
                max="2000"
                value={maxCommits}
                onChange={(e) => setMaxCommits(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-sm text-slate-100"
              />
              <span className="text-[11px] text-slate-500 mt-1 block">Default 500, max 2000 commits</span>
            </div>
          )}

          {scanMode === "patch_upload" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">Unified Diff / Patch Content</label>
                <label className="text-xs text-indigo-400 hover:text-indigo-300 cursor-pointer font-medium flex items-center gap-1">
                  <UploadCloud className="w-3.5 h-3.5" />
                  <span>Upload .diff or .patch file</span>
                  <input type="file" accept=".diff,.patch,text/plain" onChange={handleFileUpload} className="hidden" />
                </label>
              </div>
              <textarea
                rows={5}
                value={patchText}
                onChange={(e) => setPatchText(e.target.value)}
                placeholder="Paste unified diff here:&#10;diff --git a/app.py b/app.py&#10;--- a/app.py&#10;+++ b/app.py&#10;@@ -6,2 +6,0 @@&#10;-    if '..' in filename: raise ValueError()"
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          {/* Optional Private Token Field */}
          {scanMode !== "patch_upload" && (
            <div className="pt-2">
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="text-xs font-medium text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
              >
                <Lock className="w-3.5 h-3.5 text-slate-500" />
                <span>{showToken ? "Hide access token field" : "Private repository? Add GitHub Personal Access Token"}</span>
              </button>
              {showToken && (
                <div className="mt-2.5 p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1">
                  <input
                    type="password"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                  <p className="text-[11px] text-slate-500">
                    Encrypted at rest with Fernet. Stripped from git remote URLs and logs immediately after clone.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Action Button */}
          <div className="pt-2 flex items-center justify-between">
            <span className="text-[11px] text-slate-500">
              Subprocess execution with core.hooksPath=/dev/null &amp; blob filtering
            </span>
            <button
              type="submit"
              disabled={submitting || (scanMode !== "patch_upload" && !isValidUrl)}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/30 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Queueing...</span>
                </>
              ) : (
                <>
                  <FolderGit2 className="w-4 h-4" />
                  <span>Clone &amp; Scan</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Repo Cards Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-white">Active Codebases ({repos.length})</h2>
          <button
            onClick={onRefresh}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {repos.length === 0 ? (
          /* Empty State */
          <div className="p-12 rounded-2xl bg-slate-900/60 border border-slate-800/80 text-center space-y-5">
            <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center mx-auto">
              <FolderGit2 className="w-6 h-6" />
            </div>
            <div className="max-w-md mx-auto">
              <h3 className="text-base font-bold text-white">Paste a GitHub link to get started</h3>
              <p className="text-xs text-slate-400 mt-1">
                PRSentinel will clone the repository history, inspect open PRs, and cross-reference removed lines against known security fixes.
              </p>
            </div>

            {/* Example Public Repos Clearly Labeled */}
            <div className="pt-4 border-t border-slate-800/60 max-w-lg mx-auto">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-3">
                Try with public example repositories (Sample Data):
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  onClick={() => handleExampleClick("https://github.com/pallets/flask")}
                  className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/60 text-left transition-all group"
                >
                  <div className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300">
                    pallets/flask
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Flask Web Framework (Public example)</div>
                </button>
                <button
                  onClick={() => handleExampleClick("https://github.com/psf/requests")}
                  className="p-3 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/60 text-left transition-all group"
                >
                  <div className="text-xs font-semibold text-slate-200 group-hover:text-indigo-300">
                    psf/requests
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5">Python HTTP Library (Public example)</div>
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* Repo Cards Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repos.map((repo) => {
              const statusColors = {
                ready: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
                cloning: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30 animate-pulse",
                failed: "bg-rose-500/10 text-rose-400 border-rose-500/30",
                pending: "bg-amber-500/10 text-amber-400 border-amber-500/30",
              }[repo.clone_status] || "bg-slate-800 text-slate-400 border-slate-700";

              return (
                <div
                  key={repo.id}
                  className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="text-[11px] text-slate-400 font-mono block truncate">{repo.owner}</span>
                        <h3 className="text-base font-bold text-white truncate">{repo.name}</h3>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase border shrink-0 ${statusColors}`}>
                        {repo.clone_status}
                      </span>
                    </div>

                    <div className="mt-4 space-y-2 text-xs text-slate-400">
                      <div className="flex items-center gap-1.5">
                        <GitBranch className="w-3.5 h-3.5 text-slate-500" />
                        <span>Branch: <strong className="text-slate-300">{repo.default_branch}</strong></span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Findings discovered:</span>
                        <span
                          onClick={() => onNavigateToFindings(repo.id)}
                          className={`font-semibold cursor-pointer ${
                            repo.findings_count > 0 ? "text-rose-400 hover:underline" : "text-slate-400"
                          }`}
                        >
                          {repo.findings_count}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 pt-1">
                        Last scanned: {repo.last_scanned_at ? new Date(repo.last_scanned_at).toLocaleString() : "Never"}
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleRescan(repo.id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition-colors"
                        title="Rescan open PRs"
                      >
                        Rescan PRs
                      </button>
                      <button
                        onClick={() => handlePullLatest(repo.id)}
                        className="px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition-colors"
                        title="Pull latest commits & audit"
                      >
                        Pull Latest
                      </button>
                    </div>
                    <button
                      onClick={() => handleDelete(repo.id, `${repo.owner}/${repo.name}`)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Remove repository"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}


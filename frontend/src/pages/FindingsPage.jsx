import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  AlertOctagon,
  AlertTriangle,
  CheckCircle,
  X,
  ExternalLink,
  Search,
  Filter,
  Check,
  Ban,
  Clock,
  ArrowRight,
  GitCommit,
  FileCode,
  Sparkles,
} from "lucide-react";
import { api } from "../api/client";
import { RiskBadge, StatusChip } from "../components/RiskBadge";
import { SemicircleGauge } from "../components/SemicircleGauge";
import { useToast } from "../components/Toast";

export function FindingsPage({ initialLevelFilter = "", initialRepoFilter = "", selectedFindingId, onCloseSelected }) {
  const { addToast } = useToast();

  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filters
  const [levelFilter, setLevelFilter] = useState(initialLevelFilter);
  const [statusFilter, setStatusFilter] = useState("");
  const [modeFilter, setModeFilter] = useState("");
  const [search, setSearch] = useState("");

  // Drawer
  const [activeFinding, setActiveFinding] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [triageLoading, setTriageLoading] = useState(false);

  const fetchFindings = async () => {
    setLoading(true);
    try {
      const data = await api.getFindings({
        level: levelFilter || undefined,
        status: statusFilter || undefined,
        mode: modeFilter || undefined,
        search: search || undefined,
        repo_id: initialRepoFilter || undefined,
      });
      setFindings(data);

      if (selectedFindingId) {
        const found = data.find((f) => f.id === selectedFindingId);
        if (found) {
          setActiveFinding(found);
          setDrawerOpen(true);
        }
      }
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFindings();
  }, [levelFilter, statusFilter, modeFilter, search, initialRepoFilter, selectedFindingId]);

  // Handle drawer open on row click
  const handleRowClick = (finding) => {
    setActiveFinding(finding);
    setDrawerOpen(true);
  };

  // Close drawer with Esc key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") {
        setDrawerOpen(false);
        if (onCloseSelected) onCloseSelected();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleStatusUpdate = async (newStatus) => {
    if (!activeFinding) return;
    setTriageLoading(true);
    try {
      const updated = await api.updateFindingStatus(activeFinding.id, newStatus);
      setActiveFinding(updated);
      setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
      const statusLabels = {
        confirmed_threat: "Confirmed Threat 🚨",
        false_positive: "Marked as Safe (False Positive) ✅",
        dismissed: "Dismissed ✕",
        open: "Reopened for review",
      };
      addToast(`Finding updated: ${statusLabels[newStatus] || newStatus}`);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setTriageLoading(false);
    }
  };

  // Compute real header stats
  const totalCount = findings.length;
  const highCount = findings.filter((f) => f.level === "HIGH").length;
  const medCount = findings.filter((f) => f.level === "MEDIUM").length;
  const lowCount = findings.filter((f) => f.level === "LOW").length;
  const openCount = findings.filter((f) => f.status === "open").length;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Security Findings</h1>
        <p className="text-sm text-slate-400 mt-1">
          Review potential fix reversals, inspect side-by-side AST evidence, and triage detected threats.
        </p>
      </div>

      {/* Header Stat Row (Real Data) */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-[11px] font-semibold text-slate-400">Total Findings</span>
          <div className="text-2xl font-bold text-white mt-1">{totalCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20">
          <span className="text-[11px] font-semibold text-rose-300">🚨 HIGH Risk</span>
          <div className="text-2xl font-bold text-rose-400 mt-1">{highCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <span className="text-[11px] font-semibold text-amber-300">⚠️ MEDIUM Risk</span>
          <div className="text-2xl font-bold text-amber-400 mt-1">{medCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
          <span className="text-[11px] font-semibold text-emerald-300">✅ LOW Risk</span>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{lowCount}</div>
        </div>
        <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
          <span className="text-[11px] font-semibold text-indigo-300">Pending Review</span>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{openCount}</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          {/* Level Filter */}
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Risk Levels</option>
            <option value="HIGH">🚨 HIGH Risk</option>
            <option value="MEDIUM">⚠️ MEDIUM Risk</option>
            <option value="LOW">✅ LOW Risk</option>
          </select>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Statuses</option>
            <option value="open">Open Review</option>
            <option value="confirmed_threat">Confirmed Threat</option>
            <option value="false_positive">False Positive</option>
            <option value="dismissed">Dismissed</option>
          </select>

          {/* Mode Filter */}
          <select
            value={modeFilter}
            onChange={(e) => setModeFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="">All Scan Modes</option>
            <option value="open_prs">Open PRs</option>
            <option value="single_pr">Single PR</option>
            <option value="history_audit">History Audit</option>
            <option value="branch_compare">Branch Compare</option>
            <option value="patch_upload">Patch Upload</option>
          </select>
        </div>

        {/* Search */}
        <div className="relative w-64">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search path, CVE, ref..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Findings Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-16 text-center text-xs text-slate-500">Loading findings...</div>
        ) : findings.length === 0 ? (
          <div className="p-16 text-center text-xs text-slate-500 space-y-2">
            <CheckCircle className="w-8 h-8 text-emerald-500/40 mx-auto" />
            <p className="font-semibold text-slate-300">No findings matched your criteria</p>
            <p className="text-slate-500">All scanned changes conform to registered safety policies.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Risk / Score</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Target Ref</th>
                  <th className="py-3 px-4">File Path</th>
                  <th className="py-3 px-4">Associated Fix</th>
                  <th className="py-3 px-4 text-right">Detected</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {findings.map((f) => (
                  <tr
                    key={f.id}
                    onClick={() => handleRowClick(f)}
                    className="hover:bg-slate-800/50 cursor-pointer transition-colors group"
                  >
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <RiskBadge level={f.level} score={f.score} />
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusChip status={f.status} />
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="font-semibold text-white group-hover:text-indigo-300 transition-colors">
                        {f.target_ref}
                      </span>
                      <span className="text-[10px] text-slate-500 block truncate max-w-[180px]">{f.title}</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300 truncate max-w-[200px]">
                      {f.file_path}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono text-[11px]">
                        {f.fix_id || "Fix Reversal"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-right text-slate-500 whitespace-nowrap font-mono text-[11px]">
                      {new Date(f.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Slide-out Drawer */}
      {drawerOpen && activeFinding && (
        <div className="fixed inset-0 z-50 flex justify-end">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
            onClick={() => setDrawerOpen(false)}
          />

          {/* Drawer Panel */}
          <div className="relative w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full overflow-y-auto p-6 space-y-6 shadow-2xl z-10 animate-slideInRight">
            {/* Drawer Header */}
            <div className="flex items-start justify-between pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <RiskBadge level={activeFinding.level} score={activeFinding.score} />
                  <StatusChip status={activeFinding.status} />
                </div>
                <h2 className="text-lg font-bold text-white">{activeFinding.title}</h2>
                <div className="flex items-center gap-2 text-xs text-slate-400 font-mono mt-1">
                  <span>File: {activeFinding.file_path}</span>
                  <span>&bull;</span>
                  <span>Ref: {activeFinding.target_ref}</span>
                </div>
              </div>

              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                aria-label="Close drawer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Score & Gauge Section */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-around">
              <SemicircleGauge score={activeFinding.score} level={activeFinding.level} />

              <div className="flex-1 pl-6 space-y-2">
                <span className="text-xs font-semibold text-slate-300">Deterministic Multi-Signal Scoring</span>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Evaluated using sequence similarity, sensitive token removal patterns, cleanup title mismatches, and author contribution history.
                </p>
                <div className="text-[11px] font-mono text-indigo-400 pt-1">
                  Rule ID: {activeFinding.fix_id || "HEURISTIC-DETECTION"}
                </div>
              </div>
            </div>

            {/* Plain-English Summary */}
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-500/30 space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-300">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>Plain-English Risk Summary</span>
              </div>
              <p className="text-xs text-slate-200 leading-relaxed">
                {activeFinding.summary ||
                  "This pull request removes code matching a past security fix. Merging without verification could reintroduce the vulnerability."}
              </p>
            </div>

            {/* Score Breakdown Bars */}
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Score Breakdown</h3>
              <div className="space-y-2">
                {(activeFinding.breakdown || []).map((b, i) => (
                  <div key={i} className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 flex items-center justify-between text-xs">
                    <span className="text-slate-300 font-medium">{b.reason}</span>
                    <span
                      className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
                        b.points > 0 ? "text-rose-400 bg-rose-500/10" : "text-emerald-400 bg-emerald-500/10"
                      }`}
                    >
                      {b.points > 0 ? `+${b.points}` : b.points} pts
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Side-by-Side Evidence Comparison */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Differential Code Evidence
                </h3>
                <span className="text-[11px] text-slate-500 font-mono">Original Fix vs Removed Lines</span>
              </div>

              {(activeFinding.evidence || []).map((ev, i) => (
                <div key={i} className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden">
                  <div className="px-3 py-2 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 font-mono">{ev.file || activeFinding.file_path}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                      {Math.round((ev.similarity || 1.0) * 100)}% Match in Reverse
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-slate-800 text-xs font-mono">
                    {/* Left: Original Fix Lines */}
                    <div className="p-3 bg-emerald-950/20">
                      <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider mb-2">
                        + Original Fix Check Added:
                      </div>
                      <div className="space-y-1 text-slate-300 overflow-x-auto">
                        {(ev.fix_lines || [ev.fix_commit_subject || "Security validation statement"]).map((l, idx) => (
                          <div key={idx} className="text-emerald-300/90 whitespace-pre">
                            {l}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Right: Lines Removed in PR */}
                    <div className="p-3 bg-rose-950/20">
                      <div className="text-[10px] font-bold text-rose-400 uppercase tracking-wider mb-2">
                        - Check Deleted in this Change:
                      </div>
                      <div className="space-y-1 text-slate-300 overflow-x-auto">
                        {(ev.removed_lines || ev.deleted_lines || [ev.reverting_commit_subject || "Validation deleted"]).map((l, idx) => (
                          <div key={idx} className="text-rose-300/90 whitespace-pre">
                            {l}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Rendered PR Comment Preview */}
            <div className="space-y-2">
              <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Rendered GitHub Action Sticky Comment Preview
              </h3>
              <pre className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 whitespace-pre-wrap leading-relaxed">
                {activeFinding.comment_preview ||
                  `<!-- prsentinel -->\n## PRSentinel: ${activeFinding.score} / 100 ${activeFinding.level} RISK\n\n- ${activeFinding.reasons.join(
                    "\n- "
                  )}\n\n**Advice: Review carefully before merging.**`}
              </pre>
            </div>

            {/* Triage Actions */}
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <span className="text-xs font-semibold text-slate-300 block">Triage Finding</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleStatusUpdate("confirmed_threat")}
                  disabled={triageLoading}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 shadow-md shadow-rose-600/30 transition-colors disabled:opacity-50"
                >
                  <AlertOctagon className="w-3.5 h-3.5" />
                  <span>Confirm Threat</span>
                </button>
                <button
                  onClick={() => handleStatusUpdate("false_positive")}
                  disabled={triageLoading}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 transition-colors disabled:opacity-50"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Mark Safe (FP)</span>
                </button>
                <button
                  onClick={() => handleStatusUpdate("dismissed")}
                  disabled={triageLoading}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-400 bg-slate-800 hover:bg-slate-700 hover:text-white transition-colors disabled:opacity-50"
                >
                  <Ban className="w-3.5 h-3.5" />
                  <span>Dismiss</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


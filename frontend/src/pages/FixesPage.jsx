import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Plus,
  Download,
  Trash2,
  Edit,
  ExternalLink,
  CheckCircle2,
  Terminal,
  FileCode,
  ToggleLeft,
  ToggleRight,
  AlertTriangle,
  Sparkles,
  X,
  Play,
} from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";
import { RiskBadge } from "../components/RiskBadge";

export function FixesPage({ initialTestOpen = false }) {
  const { addToast } = useToast();

  const [fixes, setFixes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Modal: Add / Import Fix
  const [modalOpen, setModalOpen] = useState(false);
  const [importId, setImportId] = useState("");
  const [importCommitUrl, setImportCommitUrl] = useState("");
  const [importPreview, setImportPreview] = useState(null);
  const [importing, setImporting] = useState(false);

  // Manual Add state
  const [manualMode, setManualMode] = useState(false);
  const [manualId, setManualId] = useState("");
  const [manualDesc, setManualDesc] = useState("");
  const [manualFile, setManualFile] = useState("app.py");
  const [manualSeverity, setManualSeverity] = useState("HIGH");
  const [manualLines, setManualLines] = useState("");

  // Test Rule Panel
  const [testPanelOpen, setTestPanelOpen] = useState(initialTestOpen);
  const [testDiff, setTestDiff] = useState(
    `diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@ -6,2 +6,0 @@\n-    if ".." in filename or filename.startswith("/"):\n-        raise ValueError("Invalid file path")`
  );
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  const fetchFixes = async () => {
    setLoading(true);
    try {
      const data = await api.getFixes();
      setFixes(data);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFixes();
  }, []);

  const handleToggle = async (fix) => {
    try {
      const updated = await api.updateFix(fix.id, { enabled: !fix.enabled });
      setFixes((prev) => prev.map((f) => (f.id === fix.id ? updated : f)));
      addToast(`Rule ${fix.id} ${updated.enabled ? "enabled" : "disabled"}`);
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleDelete = async (fixId) => {
    if (!confirm(`Are you sure you want to delete fix rule ${fixId}?`)) return;
    try {
      await api.deleteFix(fixId);
      setFixes((prev) => prev.filter((f) => f.id !== fixId));
      addToast(`Rule ${fixId} deleted`);
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleImportPreview = async () => {
    if (!importId && !importCommitUrl) {
      addToast("Please provide a CVE/GHSA ID or commit URL", "warn");
      return;
    }
    setImporting(true);
    try {
      const preview = await api.importFix({
        id: importId.trim() || undefined,
        commit_url: importCommitUrl.trim() || undefined,
        preview_only: true,
      });
      setImportPreview(preview);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setImporting(false);
    }
  };

  const handleSaveImportedFix = async () => {
    setImporting(true);
    try {
      const saved = await api.importFix({
        id: importId.trim() || undefined,
        commit_url: importCommitUrl.trim() || undefined,
        preview_only: false,
      });
      addToast(`Rule ${saved.id} imported and registered!`);
      setModalOpen(false);
      setImportId("");
      setImportCommitUrl("");
      setImportPreview(null);
      fetchFixes();
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setImporting(false);
    }
  };

  const handleCreateManualFix = async (e) => {
    e.preventDefault();
    const lines = manualLines
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    if (lines.length === 0) {
      addToast("Please provide at least one fix added code line", "warn");
      return;
    }

    try {
      await api.createFix({
        id: manualId.trim(),
        description: manualDesc.trim(),
        file: manualFile.trim(),
        package: "core",
        severity: manualSeverity,
        verified: false,
        enabled: true,
        fix_added_lines: lines,
      });
      addToast(`Rule ${manualId} created successfully!`);
      setModalOpen(false);
      setManualId("");
      setManualDesc("");
      setManualLines("");
      fetchFixes();
    } catch (err) {
      addToast(err.message, "error");
    }
  };

  const handleRunRuleTest = async () => {
    if (!testDiff.trim()) {
      addToast("Please enter a diff to test", "warn");
      return;
    }
    setTesting(true);
    try {
      const result = await api.testRule({
        diff: testDiff,
        title: "Rule Test Simulation",
      });
      setTestResult(result);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Title & Actions */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Security Fix Registry</h1>
          <p className="text-sm text-slate-400 mt-1">
            Deterministic rules defining past vulnerability patches. Pull requests removing these statements trigger HIGH alerts.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setTestPanelOpen(!testPanelOpen)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-700/80 transition-colors"
          >
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>{testPanelOpen ? "Hide Test Workbench" : "Test Rule Workbench"}</span>
          </button>
          <button
            onClick={() => {
              setModalOpen(true);
              setImportPreview(null);
            }}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add / Import Fix</span>
          </button>
        </div>
      </div>

      {/* Interactive "Test This Rule" Workbench Panel */}
      {testPanelOpen && (
        <div className="p-6 rounded-2xl bg-slate-900 border border-indigo-500/30 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white">Interactive Rule Test Workbench</h3>
            </div>
            <span className="text-xs text-slate-400">Deterministic AST &amp; line matching</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Diff Input */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 block">Unified Diff to Test</label>
              <textarea
                rows={8}
                value={testDiff}
                onChange={(e) => setTestDiff(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed"
                placeholder="diff --git a/app.py b/app.py..."
              />
              <button
                onClick={handleRunRuleTest}
                disabled={testing}
                className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors disabled:opacity-50"
              >
                <Play className="w-3.5 h-3.5" />
                <span>{testing ? "Testing..." : "Simulate Rule Detection"}</span>
              </button>
            </div>

            {/* Test Simulation Results */}
            <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-3">
              <span className="text-xs font-semibold text-slate-300 block">Simulation Result</span>
              {testResult ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <RiskBadge level={testResult.level} score={testResult.score} />
                    <span className="text-xs text-slate-400">
                      {testResult.moved_lines_detected ? "(Moved lines detected)" : "(Direct match)"}
                    </span>
                  </div>

                  {/* Summary */}
                  <div className="p-2.5 rounded-lg bg-slate-900 text-xs text-slate-300 border border-slate-800">
                    {testResult.summary}
                  </div>

                  {/* Reasons list */}
                  <ul className="text-xs text-slate-400 space-y-1 list-disc pl-4">
                    {testResult.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="py-12 text-center text-xs text-slate-600 italic">
                  Paste or edit the test diff and click "Simulate Rule Detection" to view results.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Fix Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {fixes.map((fix) => {
          // Verification badge
          const badgeConfig =
            fix.source === "osv"
              ? { text: "Verified from OSV", style: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" }
              : fix.source === "demo"
              ? { text: "Demo Fix", style: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30" }
              : { text: "Unverified Custom", style: "bg-amber-500/10 text-amber-400 border-amber-500/30" };

          const isStandardVuln = fix.id.startsWith("CVE-") || fix.id.startsWith("GHSA-");
          const externalLink = isStandardVuln
            ? `https://osv.dev/vulnerability/${fix.id}`
            : fix.commit_url || null;

          return (
            <div
              key={fix.id}
              className={`p-5 rounded-xl bg-slate-900 border transition-all flex flex-col justify-between ${
                fix.enabled ? "border-slate-800 hover:border-slate-700" : "border-slate-800/40 opacity-60"
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono font-bold text-sm text-white">{fix.id}</span>
                      {externalLink && (
                        <a
                          href={externalLink}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-500 hover:text-indigo-400 transition-colors"
                          title="Open OSV / commit reference"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                    <span className="text-[11px] font-mono text-slate-400 block mt-0.5">{fix.file}</span>
                  </div>

                  {/* Enable / Disable Toggle */}
                  <button
                    onClick={() => handleToggle(fix)}
                    className="p-1 text-slate-400 hover:text-white transition-colors focus:outline-none"
                    title={fix.enabled ? "Disable rule" : "Enable rule"}
                  >
                    {fix.enabled ? (
                      <ToggleRight className="w-6 h-6 text-indigo-400" />
                    ) : (
                      <ToggleLeft className="w-6 h-6 text-slate-600" />
                    )}
                  </button>
                </div>

                {/* Description */}
                <p className="text-xs text-slate-300 mt-2.5 line-clamp-2">{fix.description}</p>

                {/* Badges */}
                <div className="flex items-center gap-2 mt-3">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badgeConfig.style}`}>
                    {badgeConfig.text}
                  </span>
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                    {fix.severity}
                  </span>
                </div>

                {/* Wrapping Code Blocks of Added Lines */}
                <div className="mt-4">
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Protected Fix Statements:
                  </span>
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/90 font-mono text-[11px] text-emerald-400 space-y-1 overflow-x-auto whitespace-pre-wrap break-all max-h-32">
                    {(fix.fix_added_lines || []).map((line, idx) => (
                      <div key={idx}>+ {line}</div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Bottom Actions */}
              <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-[11px] text-slate-500 font-mono">
                  {fix.enabled ? "Active in engine" : "Disabled"}
                </span>
                <button
                  onClick={() => handleDelete(fix.id)}
                  className="p-1 text-slate-500 hover:text-rose-400 transition-colors"
                  title="Delete rule"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add / Import Fix Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setModalOpen(false)} />
          <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl z-10 space-y-5 animate-scaleUp">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white">Add Security Fix Rule</h3>
              <button onClick={() => setModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mode switch */}
            <div className="flex items-center gap-2 p-1 rounded-xl bg-slate-950 border border-slate-800">
              <button
                type="button"
                onClick={() => setManualMode(false)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  !manualMode ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Import from OSV (CVE / GHSA)
              </button>
              <button
                type="button"
                onClick={() => setManualMode(true)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                  manualMode ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Define Custom Rule
              </button>
            </div>

            {!manualMode ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Advisory ID (CVE or GHSA)
                  </label>
                  <input
                    type="text"
                    value={importId}
                    onChange={(e) => setImportId(e.target.value)}
                    placeholder="e.g. CVE-2021-44228 or GHSA-jfh8-c2jp-5v3q"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    Queries https://api.osv.dev/v1/vulns/{importId || "<id>"}
                  </span>
                </div>

                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={handleImportPreview}
                    disabled={importing}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 transition-colors"
                  >
                    {importing ? "Fetching..." : "Fetch Preview"}
                  </button>
                </div>

                {/* Preview Box */}
                {importPreview && (
                  <div className="p-4 rounded-xl bg-slate-950 border border-indigo-500/40 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-indigo-300">{importPreview.id}</span>
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        Verified from OSV
                      </span>
                    </div>
                    <p className="text-xs text-slate-300">{importPreview.description}</p>
                    <div className="text-[11px] text-slate-400">
                      Target File: <code className="text-white font-mono">{importPreview.file}</code>
                    </div>

                    <button
                      type="button"
                      onClick={handleSaveImportedFix}
                      className="w-full py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md transition-colors"
                    >
                      Confirm &amp; Register Rule
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <form onSubmit={handleCreateManualFix} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Rule ID</label>
                  <input
                    type="text"
                    required
                    value={manualId}
                    onChange={(e) => setManualId(e.target.value)}
                    placeholder="CVE-2024-CUSTOM-01"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
                  <input
                    type="text"
                    required
                    value={manualDesc}
                    onChange={(e) => setManualDesc(e.target.value)}
                    placeholder="Prevents unauthorized admin deletion"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Target File</label>
                    <input
                      type="text"
                      required
                      value={manualFile}
                      onChange={(e) => setManualFile(e.target.value)}
                      placeholder="admin.py"
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">Severity</label>
                    <select
                      value={manualSeverity}
                      onChange={(e) => setManualSeverity(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white"
                    >
                      <option value="CRITICAL">CRITICAL</option>
                      <option value="HIGH">HIGH</option>
                      <option value="MODERATE">MODERATE</option>
                      <option value="LOW">LOW</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Protected Code Statements (One per line)
                  </label>
                  <textarea
                    rows={3}
                    required
                    value={manualLines}
                    onChange={(e) => setManualLines(e.target.value)}
                    placeholder="if not current_user.is_admin:&#10;raise PermissionError('Admin access required')"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 font-mono text-xs text-white"
                  />
                </div>

                <div className="pt-2 flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setModalOpen(false)}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-5 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md"
                  >
                    Create Rule
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


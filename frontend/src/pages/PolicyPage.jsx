import React, { useState, useEffect } from "react";
import {
  Sliders,
  ShieldAlert,
  Save,
  CheckCircle2,
  AlertTriangle,
  Info,
  ToggleLeft,
  ToggleRight,
  Plus,
  X,
} from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

export function PolicyPage() {
  const { addToast } = useToast();

  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form states
  const [failOnLevel, setFailOnLevel] = useState("HIGH");
  const [failOnScore, setFailOnScore] = useState(70);
  const [sensitiveKeywords, setSensitiveKeywords] = useState([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [protectedPaths, setProtectedPaths] = useState([]);
  const [newPath, setNewPath] = useState("");
  const [trustedAuthors, setTrustedAuthors] = useState([]);
  const [newAuthor, setNewAuthor] = useState("");
  const [signalToggles, setSignalToggles] = useState({
    fix_reversal: true,
    sensitive_keywords: true,
    cleanup_title: true,
    account_age: true,
    first_time: true,
  });

  const fetchPolicy = async () => {
    setLoading(true);
    try {
      const p = await api.getPolicy();
      setPolicy(p);
      setFailOnLevel(p.fail_on_level || "HIGH");
      setFailOnScore(p.fail_on_score || 70);
      setSensitiveKeywords(p.sensitive_keywords || []);
      setProtectedPaths(p.protected_paths || []);
      setTrustedAuthors(p.trusted_authors || []);
      setSignalToggles(p.signal_toggles || {});
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicy();
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updatePolicy({
        fail_on_level: failOnLevel,
        fail_on_score: Number(failOnScore),
        sensitive_keywords: sensitiveKeywords,
        protected_paths: protectedPaths,
        trusted_authors: trustedAuthors,
        signal_toggles: signalToggles,
      });
      setPolicy(updated);
      addToast("Security policy saved successfully! Changes apply on next scan.", "success");
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setSaving(false);
    }
  };

  const addKeyword = () => {
    const val = newKeyword.trim().toLowerCase();
    if (val && !sensitiveKeywords.includes(val)) {
      setSensitiveKeywords([...sensitiveKeywords, val]);
      setNewKeyword("");
    }
  };

  const removeKeyword = (kw) => {
    setSensitiveKeywords(sensitiveKeywords.filter((k) => k !== kw));
  };

  const addPath = () => {
    const val = newPath.trim();
    if (val && !protectedPaths.includes(val)) {
      setProtectedPaths([...protectedPaths, val]);
      setNewPath("");
    }
  };

  const removePath = (p) => {
    setProtectedPaths(protectedPaths.filter((x) => x !== p));
  };

  const addAuthor = () => {
    const val = newAuthor.trim();
    if (val && !trustedAuthors.includes(val)) {
      setTrustedAuthors([...trustedAuthors, val]);
      setNewAuthor("");
    }
  };

  const removeAuthor = (a) => {
    setTrustedAuthors(trustedAuthors.filter((x) => x !== a));
  };

  const toggleSignal = (key) => {
    setSignalToggles({ ...signalToggles, [key]: !signalToggles[key] });
  };

  if (loading) {
    return <div className="p-16 text-center text-xs text-slate-500">Loading security policy...</div>;
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Title */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Detection &amp; CI Policy</h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure risk thresholds, signal weights, sensitive patterns, and trusted author exemptions.
          </p>
        </div>

        {/* Notice Banner */}
        <div className="px-3.5 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs font-semibold flex items-center gap-2">
          <Info className="w-4 h-4 text-indigo-400" />
          <span>Changes apply on next scan</span>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Fail-on Thresholds */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <span>Failure Thresholds &amp; CI Gating</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Block PR on Risk Level
              </label>
              <select
                value={failOnLevel}
                onChange={(e) => setFailOnLevel(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="HIGH">🚨 HIGH Risk (Score &ge; 70)</option>
                <option value="MEDIUM">⚠️ MEDIUM Risk (Score &ge; 40)</option>
                <option value="LOW">✅ LOW Risk</option>
                <option value="NEVER">NEVER (Advisory only)</option>
              </select>
              <span className="text-[11px] text-slate-500 mt-1 block">
                Fails GitHub Action status checks if PR score meets or exceeds this severity.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Custom Point Cutoff (0-100)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="30"
                  max="95"
                  value={failOnScore}
                  onChange={(e) => setFailOnScore(e.target.value)}
                  className="flex-1 accent-indigo-500"
                />
                <span className="font-mono font-bold text-sm text-indigo-400 w-12 text-right">
                  {failOnScore} pts
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-1 block">
                PRs scoring above this cutoff are flagged for mandatory maintainer sign-off.
              </span>
            </div>
          </div>
        </div>

        {/* Signal Toggles */}
        <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Sliders className="w-4 h-4 text-indigo-400" />
            <span>Multi-Signal Detection Toggles</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {[
              { id: "fix_reversal", label: "Known Fix Reversal (+60-75 pts)", desc: "Matches deleted code against registered CVE fixes" },
              { id: "sensitive_keywords", label: "Sensitive Validation Deleted (+10 pts)", desc: "Flags deletion of auth, validation, or sanitization statements" },
              { id: "cleanup_title", label: "PR Title Deception (+5 pts)", desc: "Detects 'clean' or 'refactor' titles masking check removals" },
              { id: "account_age", label: "Young Account Origin (+15 pts)", desc: "Applies elevated scrutiny to GitHub accounts under 30 days old" },
              { id: "first_time", label: "First-time Contributor (+10 pts)", desc: "Extra scrutiny for authors with no previous merged commits" },
            ].map((sig) => {
              const enabled = signalToggles[sig.id] ?? true;
              return (
                <div
                  key={sig.id}
                  onClick={() => toggleSignal(sig.id)}
                  className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between cursor-pointer hover:border-slate-700 transition-all select-none"
                >
                  <div className="pr-4">
                    <span className="text-xs font-semibold text-white block">{sig.label}</span>
                    <span className="text-[11px] text-slate-500">{sig.desc}</span>
                  </div>
                  <button type="button" className="text-slate-400 focus:outline-none">
                    {enabled ? (
                      <ToggleRight className="w-6 h-6 text-indigo-400" />
                    ) : (
                      <ToggleLeft className="w-6 h-6 text-slate-600" />
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Sensitive Keywords & Protected Paths */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Sensitive Keywords */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-white">Sensitive Keywords</h3>
            <p className="text-xs text-slate-400">Tokens indicating safety checks when removed in diffs:</p>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
                placeholder="Add keyword (e.g. rate_limit)"
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={addKeyword}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5 pt-2 max-h-40 overflow-y-auto">
              {sensitiveKeywords.map((kw, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-indigo-300"
                >
                  <span>{kw}</span>
                  <button
                    type="button"
                    onClick={() => removeKeyword(kw)}
                    className="text-slate-500 hover:text-rose-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Protected Paths */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-white">Protected Path Patterns</h3>
            <p className="text-xs text-slate-400">Glob patterns subject to strict deletion audits:</p>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addPath())}
                placeholder="e.g. auth/** or security/**"
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="button"
                onClick={addPath}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5 pt-2 max-h-40 overflow-y-auto">
              {protectedPaths.map((p, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-300"
                >
                  <span>{p}</span>
                  <button
                    type="button"
                    onClick={() => removePath(p)}
                    className="text-slate-500 hover:text-rose-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Save Bar */}
        <div className="pt-2 flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/30 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? "Saving Policy..." : "Save Policy Configuration"}</span>
          </button>
        </div>
      </form>
    </div>
  );
}


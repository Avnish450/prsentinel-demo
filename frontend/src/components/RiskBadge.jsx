import React from "react";
import { AlertOctagon, AlertTriangle, CheckCircle, ShieldAlert, ShieldCheck } from "lucide-react";

export function RiskBadge({ level, score = null, size = "md" }) {
  const norm = (level || "LOW").toUpperCase();

  if (norm.includes("HIGH")) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-semibold rounded-lg border bg-rose-500/10 text-rose-400 border-rose-500/30 ${
          size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"
        }`}
        title="High security risk: Fix reversal or critical check removal detected"
      >
        <span aria-hidden="true" className="text-sm">🚨</span>
        <AlertOctagon className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
        <span>HIGH {score !== null ? `(${score})` : ""}</span>
      </span>
    );
  }

  if (norm.includes("MED")) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-semibold rounded-lg border bg-amber-500/10 text-amber-400 border-amber-500/30 ${
          size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"
        }`}
        title="Medium security risk: Validation modification or partial match"
      >
        <span aria-hidden="true" className="text-sm">⚠️</span>
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
        <span>MEDIUM {score !== null ? `(${score})` : ""}</span>
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold rounded-lg border bg-emerald-500/10 text-emerald-400 border-emerald-500/30 ${
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs"
      }`}
      title="Low security risk: No security check regressions identified"
    >
      <span aria-hidden="true" className="text-sm">✅</span>
      <CheckCircle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
      <span>LOW {score !== null ? `(${score})` : ""}</span>
    </span>
  );
}

export function StatusChip({ status }) {
  const norm = (status || "open").toLowerCase();

  const styles = {
    open: "bg-blue-500/10 text-blue-400 border-blue-500/30",
    confirmed_threat: "bg-rose-500/20 text-rose-300 border-rose-500/50",
    false_positive: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    dismissed: "bg-slate-700/30 text-slate-400 border-slate-700",
  }[norm] || "bg-slate-800 text-slate-300 border-slate-700";

  const labels = {
    open: "Open Review",
    confirmed_threat: "Confirmed Threat",
    false_positive: "False Positive",
    dismissed: "Dismissed",
  }[norm] || norm;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles}`}>
      {labels}
    </span>
  );
}


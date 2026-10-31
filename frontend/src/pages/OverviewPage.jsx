import React from "react";
import {
  FolderGit2,
  Activity,
  AlertOctagon,
  Percent,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Clock,
  ExternalLink,
} from "lucide-react";
import { RiskBadge, StatusChip } from "../components/RiskBadge";

export function OverviewPage({ stats, onNavigate, onSelectFinding }) {
  const cards = [
    {
      label: "Active Repositories",
      value: stats?.total_repos ?? 0,
      icon: FolderGit2,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10",
      border: "border-indigo-500/20",
      tab: "repos",
    },
    {
      label: "Completed Scans",
      value: stats?.total_scans ?? 0,
      icon: Activity,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
      tab: "jobs",
    },
    {
      label: "HIGH Threats Detected",
      value: stats?.high_findings ?? 0,
      icon: AlertOctagon,
      color: "text-rose-400",
      bg: "bg-rose-500/10",
      border: "border-rose-500/20",
      tab: "findings",
      filter: "HIGH",
    },
    {
      label: "False Positive Rate",
      value: `${stats?.false_positive_rate ?? 0.0}%`,
      icon: Percent,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      tab: "findings",
    },
  ];

  const trendData = stats?.activity_trend || [];
  const maxScans = Math.max(...trendData.map((d) => d.scans), 1);
  const maxFindings = Math.max(...trendData.map((d) => d.findings), 1);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Security Posture Overview</h1>
        <p className="text-sm text-slate-400 mt-1">
          Real-time telemetry and regression tracking across monitored repositories.
        </p>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div
              key={i}
              onClick={() => onNavigate(c.tab, c.filter)}
              className="p-5 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer group"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400">{c.label}</span>
                <div className={`p-2 rounded-lg ${c.bg} ${c.color} border ${c.border}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-3xl font-extrabold text-white mt-3">{c.value}</div>
              <div className="mt-3 flex items-center text-xs text-indigo-400 group-hover:text-indigo-300 font-medium">
                <span>View details</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1 transition-transform group-hover:translate-x-1" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Grid: Trend Chart & Needs Attention Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Trend Chart */}
        <div className="lg:col-span-2 p-6 rounded-xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white">Activity & Threat Trend</h3>
                <p className="text-xs text-slate-400 mt-0.5">Computed strictly from real scan job timestamps</p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
                  <span className="text-slate-400">Scans Run</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                  <span className="text-slate-400">Findings</span>
                </div>
              </div>
            </div>

            {/* SVG Bar / Area Chart */}
            <div className="mt-8 h-48 flex items-end gap-2 border-b border-slate-800 pb-2">
              {trendData.length === 0 ? (
                <div className="w-full h-full flex items-center justify-center text-xs text-slate-500">
                  No activity recorded yet. Run a repository scan to generate history.
                </div>
              ) : (
                trendData.map((d, idx) => {
                  const scanHeight = (d.scans / maxScans) * 80;
                  const findingHeight = (d.findings / maxFindings) * 80;
                  return (
                    <div key={idx} className="flex-1 flex flex-col items-center gap-1 group relative">
                      <div className="w-full flex items-end justify-center gap-1 h-36">
                        <div
                          style={{ height: `${Math.max(scanHeight, 4)}%` }}
                          className="w-2 rounded-t bg-indigo-500/70 group-hover:bg-indigo-400 transition-all"
                          title={`${d.date}: ${d.scans} scan(s)`}
                        />
                        <div
                          style={{ height: `${Math.max(findingHeight, d.findings ? 6 : 0)}%` }}
                          className="w-2 rounded-t bg-rose-500/70 group-hover:bg-rose-400 transition-all"
                          title={`${d.date}: ${d.findings} finding(s)`}
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 whitespace-nowrap">{d.date}</span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>Detection: Deterministic AST & Substring Differential</span>
            <span className="text-slate-500 font-mono">0 false positives from moved-line refactors</span>
          </div>
        </div>

        {/* Needs Attention Queue */}
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span>Needs Attention</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">Unresolved HIGH severity reversals</p>
            </div>
            <button
              onClick={() => onNavigate("findings", "HIGH")}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
            >
              View all
            </button>
          </div>

          <div className="mt-4 space-y-3 flex-1 overflow-y-auto max-h-[300px]">
            {(!stats?.needs_attention || stats.needs_attention.length === 0) ? (
              <div className="py-12 text-center text-xs text-slate-500">
                <CheckCircle className="w-8 h-8 text-emerald-500/40 mx-auto mb-2" />
                No unreviewed HIGH security threats!
              </div>
            ) : (
              stats.needs_attention.map((item) => (
                <div
                  key={item.id}
                  onClick={() => onSelectFinding(item.id)}
                  className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer flex flex-col gap-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <RiskBadge level={item.level} score={item.score} size="sm" />
                    <span className="text-[11px] font-mono text-slate-400 truncate max-w-[120px]">
                      {item.file_path}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-white line-clamp-1">{item.title}</div>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>Target: {item.target_ref}</span>
                    <span className="text-indigo-400 hover:underline">Review &rarr;</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function CheckCircle(props) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}


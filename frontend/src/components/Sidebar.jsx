import React from "react";
import {
  LayoutDashboard,
  FolderGit2,
  Activity,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  History,
  Shield,
  ExternalLink,
} from "lucide-react";

export function Sidebar({ currentTab, setCurrentTab, stats }) {
  const navItems = [
    { id: "overview", label: "Overview", icon: LayoutDashboard },
    { id: "repos", label: "Repositories", icon: FolderGit2, badge: stats?.total_repos },
    { id: "jobs", label: "Scan Jobs", icon: Activity },
    {
      id: "findings",
      label: "Findings",
      icon: ShieldAlert,
      badge: stats?.open_threats ? `${stats.open_threats} HIGH` : null,
      badgeColor: "bg-rose-500/20 text-rose-300 border border-rose-500/40",
    },
    { id: "fixes", label: "Fixes Registry", icon: ShieldCheck },
    { id: "policy", label: "Policy", icon: Sliders },
    { id: "audit", label: "Audit Log", icon: History },
  ];

  return (
    <aside className="w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col shrink-0 select-none">
      {/* Brand Logo & Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-500/25">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold text-base tracking-tight text-white">PRSentinel</span>
            <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              v2.0
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium">Fix Regression Defense</p>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/50 ${
                isActive
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30 font-semibold"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? "text-white" : "text-slate-400"}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && item.badge !== null && (
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                    item.badgeColor || (isActive ? "bg-indigo-700/60 text-white" : "bg-slate-800 text-slate-400")
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Info Card */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-200">GitHub Action</div>
            <div className="text-[11px] text-slate-400">Independent CI active</div>
          </div>
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
        </div>
      </div>
    </aside>
  );
}


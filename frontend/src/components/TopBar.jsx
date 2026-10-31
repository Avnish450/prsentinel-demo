import React from "react";
import { Search, ShieldAlert, Sparkles, Plus, Terminal } from "lucide-react";

export function TopBar({ searchQuery, setSearchQuery, onNewScan, onTestRule }) {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
      {/* Search Input */}
      <div className="relative w-80 max-w-sm">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search repositories, CVEs, PRs..."
          className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
        />
      </div>

      {/* Action Buttons & Status */}
      <div className="flex items-center gap-3">
        <button
          onClick={onTestRule}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700/80 hover:text-white border border-slate-700/70 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          <span>Test Rule</span>
        </button>

        <button
          onClick={onNewScan}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow-md shadow-indigo-600/25 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <Plus className="w-4 h-4" />
          <span>New Scan</span>
        </button>

        <div className="h-5 w-px bg-slate-800" />

        {/* Role status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-xs font-medium text-slate-300">Admin</span>
        </div>
      </div>
    </header>
  );
}


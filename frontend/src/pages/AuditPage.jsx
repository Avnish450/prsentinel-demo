import React, { useState, useEffect } from "react";
import { History, Shield, RefreshCw } from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

export function AuditPage() {
  const { addToast } = useToast();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs(60);
      setLogs(data);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">System Audit Log</h1>
          <p className="text-sm text-slate-400 mt-1">
            Immutable log of repository connections, rule modifications, and finding triage decisions.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 bg-slate-900 hover:bg-slate-800 border border-slate-800 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Logs</span>
        </button>
      </div>

      {/* Audit Log Table */}
      <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        {loading ? (
          <div className="p-16 text-center text-xs text-slate-500">Loading audit trail...</div>
        ) : logs.length === 0 ? (
          <div className="p-16 text-center text-xs text-slate-500">No audit events recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">User</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Resource</th>
                  <th className="py-3 px-4">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {logs.map((log) => {
                  const actionColor = {
                    CREATE_REPO: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
                    DELETE_REPO: "text-rose-400 bg-rose-500/10 border-rose-500/20",
                    UPDATE_FINDING_STATUS: "text-amber-400 bg-amber-500/10 border-amber-500/20",
                    IMPORT_FIX_OSV: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
                    UPDATE_POLICY: "text-purple-400 bg-purple-500/10 border-purple-500/20",
                  }[log.action] || "text-slate-300 bg-slate-800 border-slate-700";

                  return (
                    <tr key={log.id} className="hover:bg-slate-800/50 transition-colors">
                      <td className="py-3.5 px-4 font-mono text-slate-400 whitespace-nowrap">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-slate-200">{log.user}</td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${actionColor}`}>
                          {log.action}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-slate-300">
                        {log.resource_type}: {log.resource_id?.slice(0, 12)}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400 max-w-xs truncate">
                        {JSON.stringify(log.details)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}


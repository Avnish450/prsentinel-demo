import React, { useState, useEffect, useRef } from "react";
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Clock,
  Play,
  StopCircle,
  Terminal,
  RotateCw,
  FolderGit2,
  ShieldAlert,
} from "lucide-react";
import { api } from "../api/client";
import { useToast } from "../components/Toast";

const STEPPER_STAGES = [
  { id: "queued", label: "Queued" },
  { id: "cloning", label: "Cloning" },
  { id: "indexing", label: "Indexing" },
  { id: "scanning", label: "Scanning" },
  { id: "done", label: "Done" },
];

export function JobsPage({ activeJobId, onNavigateToFindings }) {
  const { addToast } = useToast();

  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(activeJobId);
  const [jobDetails, setJobDetails] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logOffset, setLogOffset] = useState(0);
  const [autoScroll, setAutoScroll] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  const logsEndRef = useRef(null);

  // Sync selectedJobId if prop changes
  useEffect(() => {
    if (activeJobId) {
      setSelectedJobId(activeJobId);
    }
  }, [activeJobId]);

  // Load jobs list
  const fetchJobs = async () => {
    try {
      const data = await api.getJobs(30);
      setJobs(data);
      if (!selectedJobId && data.length > 0) {
        setSelectedJobId(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  // Poll current job and logs every 1.5s while active
  useEffect(() => {
    if (!selectedJobId) return;

    let isMounted = true;
    let offset = 0;

    // Reset logs when switching jobs
    setLogs([]);
    setLogOffset(0);

    const poll = async () => {
      try {
        const j = await api.getJob(selectedJobId);
        if (!isMounted) return;
        setJobDetails(j);

        const logData = await api.getJobLogs(selectedJobId, offset);
        if (!isMounted) return;

        if (logData.logs && logData.logs.length > 0) {
          setLogs((prev) => [...prev, ...logData.logs]);
          offset = logData.offset;
          setLogOffset(offset);
        }

        // If still running, schedule next poll
        if (["queued", "cloning", "indexing", "scanning"].includes(j.status)) {
          timer = setTimeout(poll, 1500);
        }
      } catch (err) {
        console.error(err);
      }
    };

    let timer = setTimeout(poll, 200);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [selectedJobId]);

  // Auto scroll logs
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollTop = logsEndRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleCancel = async () => {
    if (!selectedJobId) return;
    setCancelling(true);
    try {
      await api.cancelJob(selectedJobId);
      addToast("Job cancellation requested", "warn");
      const updated = await api.getJob(selectedJobId);
      setJobDetails(updated);
    } catch (err) {
      addToast(err.message, "error");
    } finally {
      setCancelling(false);
    }
  };

  // Determine stepper stage index
  const getStageIndex = (status) => {
    if (status === "queued") return 0;
    if (status === "cloning") return 1;
    if (status === "indexing") return 2;
    if (status === "scanning") return 3;
    if (status === "done") return 4;
    return -1;
  };

  const currentStageIndex = getStageIndex(jobDetails?.status);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Execution &amp; Scan Jobs</h1>
        <p className="text-sm text-slate-400 mt-1">
          Real-time worker telemetry, secure clone sandbox isolation, and line-by-line diff audit logs.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: Job History Selector */}
        <div className="lg:col-span-1 p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col h-[700px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">Recent Jobs</h3>
            <span className="text-[11px] text-slate-500 font-mono">{jobs.length} total</span>
          </div>

          <div className="mt-3 space-y-2 overflow-y-auto flex-1 pr-1">
            {jobs.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500">No jobs recorded yet</div>
            ) : (
              jobs.map((job) => {
                const isSelected = job.id === selectedJobId;
                const statusColor = {
                  done: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
                  failed: "text-rose-400 bg-rose-500/10 border-rose-500/30",
                  cancelled: "text-slate-400 bg-slate-800 border-slate-700",
                }[job.status] || "text-indigo-400 bg-indigo-500/10 border-indigo-500/30 animate-pulse";

                return (
                  <button
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    className={`w-full p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? "bg-slate-950 border-indigo-500/80 shadow-md"
                        : "bg-slate-950/40 border-slate-800/80 hover:bg-slate-800/60"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-1">
                      <span className="text-xs font-semibold text-white capitalize">{job.mode.replace("_", " ")}</span>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${statusColor}`}>
                        {job.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-1.5 truncate">
                      Job #{job.id.slice(0, 8)}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 mt-2">
                      <span>{job.findings_count} finding(s)</span>
                      <span>{new Date(job.created_at).toLocaleTimeString()}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Live Stepper & Terminal Log */}
        <div className="lg:col-span-3 space-y-6">
          {jobDetails ? (
            <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-6">
              {/* Header Status Bar */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-white capitalize">
                      {jobDetails.mode.replace("_", " ")} Scan
                    </h2>
                    <span className="text-xs font-mono text-slate-400">({jobDetails.id})</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">{jobDetails.current_step}</p>
                </div>

                <div className="flex items-center gap-2">
                  {["queued", "cloning", "indexing", "scanning"].includes(jobDetails.status) && (
                    <button
                      onClick={handleCancel}
                      disabled={cancelling}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition-colors"
                    >
                      <StopCircle className="w-3.5 h-3.5" />
                      <span>{cancelling ? "Cancelling..." : "Cancel Job"}</span>
                    </button>
                  )}
                  {jobDetails.findings_count > 0 && (
                    <button
                      onClick={() => onNavigateToFindings(jobDetails.repo_id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 shadow transition-colors"
                    >
                      <ShieldAlert className="w-3.5 h-3.5" />
                      <span>View {jobDetails.findings_count} Finding(s) &rarr;</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Live Stepper */}
              <div className="p-5 rounded-xl bg-slate-950/80 border border-slate-800">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold text-slate-300">Scan Pipeline Progress</span>
                  <span className="text-xs font-bold text-indigo-400">{jobDetails.progress}%</span>
                </div>

                {/* Progress bar line */}
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden mb-6">
                  <div
                    className={`h-full transition-all duration-500 ${
                      jobDetails.status === "failed"
                        ? "bg-rose-500"
                        : jobDetails.status === "cancelled"
                        ? "bg-slate-500"
                        : "bg-indigo-500"
                    }`}
                    style={{ width: `${jobDetails.progress}%` }}
                  />
                </div>

                {/* Stages */}
                <div className="grid grid-cols-5 gap-2">
                  {STEPPER_STAGES.map((stage, idx) => {
                    const isDone = currentStageIndex > idx || jobDetails.status === "done";
                    const isCurrent = currentStageIndex === idx && jobDetails.status !== "done";
                    const isFailed = jobDetails.status === "failed" && currentStageIndex === idx;

                    return (
                      <div key={stage.id} className="flex flex-col items-center text-center">
                        <div
                          className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mb-1.5 transition-all ${
                            isFailed
                              ? "bg-rose-500/20 text-rose-400 border border-rose-500"
                              : isDone
                              ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500"
                              : isCurrent
                              ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/50 animate-pulse"
                              : "bg-slate-900 text-slate-600 border border-slate-800"
                          }`}
                        >
                          {isFailed ? "!" : isDone ? "✓" : idx + 1}
                        </div>
                        <span
                          className={`text-xs font-medium ${
                            isFailed
                              ? "text-rose-400 font-bold"
                              : isDone
                              ? "text-emerald-400"
                              : isCurrent
                              ? "text-indigo-300 font-semibold"
                              : "text-slate-600"
                          }`}
                        >
                          {stage.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Error Diagnostics State */}
              {jobDetails.status === "failed" && (
                <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-200 flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-semibold text-rose-300">Scan Pipeline Failed</h4>
                    <p className="text-xs text-rose-300/90 mt-1 font-mono">
                      {jobDetails.error_message || "An unexpected error occurred during execution."}
                    </p>
                    <div className="text-[11px] text-rose-400/80 mt-2">
                      Common causes: Private repository needs personal access token, rate limit exceeded, clone timeout, or repo exceeded 250MB limit.
                    </div>
                  </div>
                </div>
              )}

              {/* Streaming Log Panel (Monospace & Auto-scroll) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                    <Terminal className="w-4 h-4 text-indigo-400" />
                    <span>Real-Time Execution Logs</span>
                  </div>
                  <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoScroll}
                      onChange={(e) => setAutoScroll(e.target.checked)}
                      className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                    />
                    <span>Auto-scroll</span>
                  </label>
                </div>

                <div
                  ref={logsEndRef}
                  className="h-80 bg-slate-950 rounded-xl border border-slate-800 p-4 font-mono text-xs overflow-y-auto space-y-1.5 shadow-inner"
                >
                  {logs.length === 0 ? (
                    <div className="text-slate-600 italic">Connecting to live log stream...</div>
                  ) : (
                    logs.map((log, i) => (
                      <div key={i} className="flex items-start gap-2.5 leading-relaxed">
                        <span className="text-slate-600 shrink-0 select-none">{log.timestamp}</span>
                        <span
                          className={
                            log.level === "error"
                              ? "text-rose-400 font-semibold"
                              : log.level === "warn"
                              ? "text-amber-400"
                              : "text-slate-300"
                          }
                        >
                          {log.message}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-16 rounded-xl bg-slate-900 border border-slate-800 text-center text-slate-500">
              Select a job from the list or queue a new scan to observe live logs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


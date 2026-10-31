// API client for PRSentinel Backend

const API_BASE = "";

export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = localStorage.getItem("prsentinel_admin_token") || "prsentinel-secret-token";

  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Admin-Token": token,
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMsg = data?.detail || `API error (${response.status})`;
    throw new Error(errorMsg);
  }

  return data;
}

export const api = {
  // Repos
  getRepos: () => apiRequest("/api/repos"),
  getRepo: (id) => apiRequest(`/api/repos/${id}`),
  createRepo: (payload) => apiRequest("/api/repos", { method: "POST", body: JSON.stringify(payload) }),
  resolveRepo: (input) => apiRequest("/api/repos/resolve", { method: "POST", body: JSON.stringify({ input }) }),
  deleteRepo: (id) => apiRequest(`/api/repos/${id}`, { method: "DELETE" }),
  rescanRepo: (id, mode) => apiRequest(`/api/repos/${id}/rescan?mode=${mode || "open_prs"}`, { method: "POST" }),
  pullRepo: (id) => apiRequest(`/api/repos/${id}/pull`, { method: "POST" }),

  // Jobs
  getJobs: (limit = 20) => apiRequest(`/api/jobs?limit=${limit}`),
  getJob: (id) => apiRequest(`/api/jobs/${id}`),
  getJobLogs: (id, offset = 0) => apiRequest(`/api/jobs/${id}/logs?offset=${offset}`),
  cancelJob: (id) => apiRequest(`/api/jobs/${id}/cancel`, { method: "POST" }),
  createJob: (payload) => apiRequest("/api/jobs", { method: "POST", body: JSON.stringify(payload) }),

  // Findings
  getFindings: (params = {}) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        searchParams.append(k, v);
      }
    });
    const qs = searchParams.toString();
    return apiRequest(`/api/findings${qs ? `?${qs}` : ""}`);
  },
  getFinding: (id) => apiRequest(`/api/findings/${id}`),
  updateFindingStatus: (id, status) => apiRequest(`/api/findings/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  }),

  // Fixes
  getFixes: () => apiRequest("/api/fixes"),
  createFix: (payload) => apiRequest("/api/fixes", { method: "POST", body: JSON.stringify(payload) }),
  updateFix: (id, payload) => apiRequest(`/api/fixes/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteFix: (id) => apiRequest(`/api/fixes/${id}`, { method: "DELETE" }),
  importFix: (payload) => apiRequest("/api/fixes/import", { method: "POST", body: JSON.stringify(payload) }),

  // Policy
  getPolicy: () => apiRequest("/api/policy"),
  updatePolicy: (payload) => apiRequest("/api/policy", { method: "PUT", body: JSON.stringify(payload) }),

  // Rules test
  testRule: (payload) => apiRequest("/api/rules/test", { method: "POST", body: JSON.stringify(payload) }),

  // Stats & Audit
  getStats: () => apiRequest("/api/stats"),
  getAuditLogs: (limit = 50) => apiRequest(`/api/audit?limit=${limit}`),
  getHealth: () => apiRequest("/health"),
};


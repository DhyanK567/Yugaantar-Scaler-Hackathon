// MediLocker API Client
// All calls go to the FastAPI backend at http://localhost:8000

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

// --- Types ---
export interface DashboardData {
  total_records?: number;
  sanitised_files?: number;
  quarantined_files?: number;
  pii_detected?: number;
  canary_leaks?: number;
  clinical_preserved?: number;
  identity_precision?: number;
  identity_recall?: number;
  identity_f05?: number;
  false_merges?: number;
  recent_jobs?: JobRecord[];
  audit_events?: AuditEvent[];
}

export interface JobRecord {
  id: string;
  status: string;
  created_at: string;
  file_count?: number;
  records_processed?: number;
  pii_detected?: number;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
  severity?: string;
}

export interface Dataset {
  id: string;
  name: string;
  format: string;
  records: number;
  created_at: string;
  status: string;
}

export interface Organisation {
  id: string;
  name: string;
  type: string;
  status: string;
  records_shared?: number;
}

export interface IdentityGraph {
  nodes: { id: string; label: string; type: string }[];
  edges: { source: string; target: string; confidence: number }[];
  total_patients?: number;
  cross_hospital_links?: number;
}

export interface ThreatLabData {
  attack_simulations?: AttackResult[];
  risk_score?: number;
  vulnerabilities?: string[];
}

export interface AttackResult {
  attack_type: string;
  success: boolean;
  records_at_risk: number;
  mitigation: string;
}

export interface PrivacyIntelligence {
  pii_breakdown?: Record<string, number>;
  language_distribution?: Record<string, number>;
  risk_distribution?: Record<string, number>;
  top_identifiers?: string[];
}

export interface ResearchRequest {
  id: string;
  title: string;
  institution: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  purpose?: string;
}

export interface Settings {
  raksha_secret_set: boolean;
  output_format: string;
  quarantine_threshold: number;
  multilingual_enabled: boolean;
}

// --- Endpoints ---
export const api = {
  health: () => request<{ status: string }>("/api/health"),

  dashboard: () => request<DashboardData>("/api/dashboard"),

  organisations: () => request<Organisation[]>("/api/organisations"),

  datasets: () => request<Dataset[]>("/api/datasets"),

  createJob: (formData: FormData) =>
    fetch(`${API_BASE}/api/jobs`, { method: "POST", body: formData }).then(
      (r) => {
        if (!r.ok) throw new Error(`Job creation failed: ${r.status}`);
        return r.json();
      }
    ),

  getJob: (jobId: string) => request<JobRecord>(`/api/jobs/${jobId}`),

  downloadJob: (jobId: string) => `${API_BASE}/api/jobs/${jobId}/download`,

  identityGraph: () => request<IdentityGraph>("/api/identity-graph"),

  threatLab: () => request<ThreatLabData>("/api/threat-lab"),

  privacyIntelligence: () =>
    request<PrivacyIntelligence>("/api/privacy-intelligence"),

  researchRequests: () => request<ResearchRequest[]>("/api/research/requests"),

  createResearchRequest: (data: Partial<ResearchRequest>) =>
    request<ResearchRequest>("/api/research/requests", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  approveResearch: (id: string) =>
    request(`/api/research/requests/${id}/approve`, { method: "POST" }),

  rejectResearch: (id: string) =>
    request(`/api/research/requests/${id}/reject`, { method: "POST" }),

  auditLogs: () => request<AuditEvent[]>("/api/audit"),

  settings: () => request<Settings>("/api/settings"),

  updateSettings: (data: Partial<Settings>) =>
    request<Settings>("/api/settings", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

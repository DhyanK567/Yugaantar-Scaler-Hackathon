// Central MediLocker API Client
// Uses environment-based API URL, HttpOnly cookie sessions, timeouts, and typed contracts.

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    return `http://${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
}

const API_BASE = getApiBase();

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options?.timeoutMs ?? 20000);

  try {
    const isFormData = typeof FormData !== "undefined" && options?.body instanceof FormData;
    const headers: Record<string, string> = isFormData
      ? {}
      : { "Content-Type": "application/json" };

    const res = await fetch(`${API_BASE}${path}`, {
      credentials: "include",
      headers: {
        ...headers,
        ...(options?.headers as Record<string, string> | undefined),
      },
      ...options,
      signal: controller.signal,
    });

    if (!res.ok) {
      let msg = `Request failed (${res.status})`;
      try {
        const errBody = await res.json();
        msg = errBody.detail || errBody.message || msg;
      } catch {
        // ignore parse error
      }
      throw new ApiError(res.status, msg);
    }
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeout);
  }
}

// --- Types ---
export type MetricStatus = "NOT_RUN" | "NOT_MEASURED" | "PASS" | "WARNING" | "FAILED" | "BLOCKED";

export interface MetricCardData {
  value: number | null;
  expected?: number | null;
  planted?: number;
  display: string;
  status: MetricStatus;
  description: string;
  scope?: string;
}

export interface JobRecord {
  id: string;
  dataset_id?: string;
  organisation_id?: string;
  dataset_name?: string;
  organisation_name?: string;
  input_name?: string;
  status: string;
  current_stage?: string;
  release_decision?: string;
  created_at: number;
  started_at?: number;
  completed_at?: number;
  files_total?: number;
  files_sanitized?: number;
  files_quarantined?: number;
  records_processed?: number;
  records_linked?: number;
  identifiers_detected?: number;
  duration_secs?: number;
  safe_error_code?: string;
  events?: JobEvent[];
}

export interface JobEvent {
  id: number;
  job_id: string;
  stage: string;
  status: string;
  message: string;
  created_at: number;
}

export interface AuditEvent {
  id: number;
  timestamp: number;
  actor_id?: string;
  actor_email?: string;
  actor_role?: string;
  organisation_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  outcome: string;
  details?: string;
}

export interface DashboardOverview {
  metrics: {
    files_processed: MetricCardData;
    records_processed: MetricCardData;
    pii_detected: MetricCardData;
    clinical_preserved: MetricCardData;
    identity_precision: MetricCardData;
    canary_leaks: MetricCardData;
  };
  privacy_health: {
    overall_readiness: MetricStatus;
    latest_job_id: string | null;
    latest_job_status: string;
    critical_unresolved_risks: number;
    pending_checks: number;
    latest_verified_at: number | null;
  };
  recent_jobs: JobRecord[];
  audit_events: AuditEvent[];
  freshness: number;
}

export interface AuthMembership {
  id: string;
  organisation_id: string;
  organisation_name: string;
  org_type: string;
  role: string;
}

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  platform_role: string;
  active_org_id: string | null;
  active_role: string | null;
  memberships: AuthMembership[];
  oauth_providers: { provider: string; email: string; email_verified: number }[];
}

export interface AuthConfig {
  offline_mode?: boolean;
  smtp_enabled: boolean;
  dev_email_login_enabled?: boolean;
  google_enabled: boolean;
  google_client_id: string | null;
  google_redirect_uri: string | null;
}

export interface Organisation {
  id: string;
  name: string;
  org_type: string;
  region: string;
  status: string;
  records_contributed: number;
  joined_at: number;
}

export interface Dataset {
  id: string;
  organisation_id: string;
  organisation_name?: string;
  name: string;
  description: string;
  format: string;
  file_count: number;
  total_bytes: number;
  sha256?: string;
  status: string;
  created_at: number;
  latest_job_id?: string;
  latest_job_status?: string;
  latest_release_decision?: string;
  records?: number;
}

export interface PrivacyAssessment {
  id: string;
  job_id: string;
  dataset_id?: string;
  organisation_id?: string;
  pii_detected: number;
  residual_leakage: number;
  canary_planted: number;
  canary_leaks: number;
  canary_status: string;
  qi_risk_score: number;
  reid_risk_level: string;
  release_eligible: number;
  created_at: number;
}

export interface PrivacyIntelligence {
  status: "MEASURED" | "NOT_MEASURED";
  assessments_count: number;
  total_pii_detected: number;
  total_residual_leakage: number;
  canary_status: string;
  reid_risk_level: string;
  assessments: PrivacyAssessment[];
}

export interface IdentityGraph {
  status: "MEASURED" | "NOT_MEASURED";
  id?: string;
  job_id?: string;
  nodes: { id: string; label: string; type: string; status?: string; orgs?: string[] }[];
  edges: { source: string; target: string; confidence?: number }[];
  total_patients: number;
  cross_hospital_links: number;
  precision: number | null;
  recall: number | null;
  f05: number | null;
  false_merges: number;
  abstentions: number;
  conflicts: number;
}

export interface ClinicalReport {
  id: string;
  job_id: string;
  organisation_id?: string;
  expected_values: number;
  preserved_values: number;
  modified_values: number;
  missing_values: number;
  medication_integrity: number | null;
  dosage_integrity: number | null;
  lab_integrity: number | null;
  vital_integrity: number | null;
  fhir_integrity: string;
  created_at: number;
}

export interface AttackResult {
  attack_type: string;
  success: boolean;
  records_at_risk: number;
  mitigation: string;
}

export interface ThreatLabData {
  status: "MEASURED" | "NOT_RUN";
  risk_score: number | null;
  attack_simulations: AttackResult[];
  history: {
    id: string;
    job_id?: string;
    profile: string;
    risk_score: number;
    blocked_count: number;
    total_count: number;
    created_at: number;
  }[];
}

export interface Passport {
  id: string;
  job_id: string;
  dataset_id?: string;
  dataset_name?: string;
  organisation_id?: string;
  organisation_name?: string;
  manifest_hash: string;
  signature_status: string;
  passport_json: string;
  created_at: number;
  verified_at?: number;
}

export interface ResearchRequest {
  id: string;
  title: string;
  requestor_org: string;
  purpose: string;
  status: string;
  created_at: number;
}

export interface SettingsData {
  user: AuthUser;
  smtp_configured: boolean;
  google_configured: boolean;
  raksha_secret_set: boolean;
  output_format: string;
  quarantine_threshold: number;
  multilingual_enabled: boolean;
}

export const api = {
  // Auth
  authConfig: () => request<AuthConfig>("/api/auth/config"),
  register: (email: string, full_name: string, organisation_id?: string) =>
    request<{ status: string; message: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, full_name, organisation_id }),
    }),
  requestOtp: (email: string) =>
    request<{ status: string; message: string }>("/api/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ email, purpose: "login" }),
    }),
  verifyOtp: (email: string, code: string) =>
    request<{ user: AuthUser; token: string }>("/api/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ email, code, purpose: "login" }),
    }),
  devEmailLogin: (email: string) =>
    request<{ user: AuthUser; token: string }>("/api/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  offlineDemoLogin: (email?: string) =>
    request<{ user: AuthUser; token: string }>("/api/auth/offline-demo", {
      method: "POST",
      body: JSON.stringify(email ? { email } : {}),
    }),
  googleLoginUrl: () => request<{ auth_url: string; state: string }>("/api/auth/google/login"),
  googleCallback: (code: string, state: string) =>
    request<{ user: AuthUser; token: string }>("/api/auth/google/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    }),
  me: () => request<{ user: AuthUser }>("/api/auth/me"),
  switchOrg: (organisation_id: string) =>
    request<{ status: string; active_org_id: string }>("/api/auth/switch-org", {
      method: "POST",
      body: JSON.stringify({ organisation_id }),
    }),
  logout: () => request<{ status: string }>("/api/auth/logout", { method: "POST" }),

  // Dashboard
  dashboard: () => request<DashboardOverview>("/api/dashboard/overview"),

  // Organisations
  organisations: () => request<Organisation[]>("/api/organisations"),
  createOrganisation: (name: string, org_type: string, region: string) =>
    request<Organisation>("/api/organisations", {
      method: "POST",
      body: JSON.stringify({ name, org_type, region }),
    }),

  // Datasets & Jobs
  datasets: () => request<Dataset[]>("/api/datasets"),
  uploadDataset: (formData: FormData) =>
    request<{ dataset_id: string; job: JobRecord | null }>("/api/datasets", {
      method: "POST",
      body: formData,
      timeoutMs: 60000,
    }),
  deleteDataset: (id: string) =>
    request<{ status: string }>(`/api/datasets/${id}`, { method: "DELETE" }),
  jobs: () => request<JobRecord[]>("/api/jobs"),
  createJob: (formData: FormData) =>
    request<JobRecord>("/api/jobs", {
      method: "POST",
      body: formData,
      timeoutMs: 60000,
    }),
  getJob: (jobId: string) => request<JobRecord>(`/api/jobs/${jobId}`),
  downloadJobUrl: (jobId: string) => `${API_BASE}/api/jobs/${jobId}/download`,

  // Privacy, Identity, Clinical, Attack
  privacyIntelligence: () => request<PrivacyIntelligence>("/api/privacy-intelligence"),
  identityGraph: (jobId?: string) =>
    request<IdentityGraph>(jobId ? `/api/identity/clusters?job_id=${encodeURIComponent(jobId)}` : "/api/identity/clusters"),
  clinicalReports: () => request<ClinicalReport[]>("/api/clinical/reports"),
  threatLab: () => request<ThreatLabData>("/api/threat-lab"),
  runAttackSimulator: (job_id: string, profile = "standard-7-vector") =>
    request("/api/attack-simulator/run", {
      method: "POST",
      body: JSON.stringify({ job_id, profile }),
    }),

  // Passports
  passports: () => request<Passport[]>("/api/passports"),
  verifyPassport: (id: string) =>
    request<{ passport_id: string; integrity_valid: boolean; signature_status: string; manifest_hash: string }>(
      `/api/passports/${id}/verify`,
      { method: "POST" }
    ),
  downloadPassportUrl: (id: string, format: "json" | "html") =>
    `${API_BASE}/api/passports/${id}/download?format=${format}`,

  // Research
  researchRequests: () => request<ResearchRequest[]>("/api/research/requests"),
  createResearchRequest: (data: { title: string; institution: string; purpose?: string }) =>
    request<ResearchRequest>("/api/research/requests", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  approveResearch: (id: string) =>
    request(`/api/research/requests/${id}/approve`, { method: "POST" }),
  rejectResearch: (id: string) =>
    request(`/api/research/requests/${id}/reject`, { method: "POST" }),

  // Audit & Settings
  auditEvents: (page = 1, pageSize = 25, action?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (action) params.set("action", action);
    return request<{ events: AuditEvent[]; total: number; page: number; page_size: number }>(
      `/api/audit/events?${params.toString()}`
    );
  },
  settings: () => request<SettingsData>("/api/settings"),
  updateSettings: (data: Partial<SettingsData>) =>
    request<SettingsData>("/api/settings", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

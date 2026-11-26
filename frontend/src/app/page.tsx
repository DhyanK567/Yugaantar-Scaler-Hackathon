"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Shield,
  Activity,
  Building2,
  Lock,
  Network,
  AlertTriangle,
  BarChart3,
  Users,
  FileCheck2,
  Settings as SettingsIcon,
  Play,
  Download,
  CheckCircle2,
  XCircle,
  Database,
  Cpu,
  RefreshCw,
  Info,
  HeartPulse,
  Award,
  Upload,
  Plus,
} from "lucide-react";

const API_BASE = "http://127.0.0.1:8000/api";

export default function MediLockerConsole() {
  const [activeTab, setActiveTab] = useState("command_centre");
  const [organisations, setOrganisations] = useState<any[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>("org-hosp-a");
  const [datasets, setDatasets] = useState<any[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("practice-dev-dataset");
  const [jobsList, setJobsList] = useState<any[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");

  const [dashboardData, setDashboardData] = useState<any>(null);
  const [jobDetail, setJobDetail] = useState<any>(null);
  const [identityData, setIdentityData] = useState<any>(null);
  const [clinicalData, setClinicalData] = useState<any>(null);
  const [intelligenceData, setIntelligenceData] = useState<any>(null);
  const [attackData, setAttackData] = useState<any>(null);
  const [passportsList, setPassportsList] = useState<any[]>([]);
  const [selectedPassport, setSelectedPassport] = useState<any>(null);
  const [passportVerifyResult, setPassportVerifyResult] = useState<any>(null);
  const [researchRequests, setResearchRequests] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditEventFilter, setAuditEventFilter] = useState<string>("");
  const [settingsData, setSettingsData] = useState<any>(null);

  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [isRunningJob, setIsRunningJob] = useState(false);
  const [selectedCluster, setSelectedCluster] = useState<any>(null);

  // Upload state
  const [uploadName, setUploadName] = useState("");
  const [uploadFiles, setUploadFiles] = useState<FileList | null>(null);

  // New Org form state
  const [newOrgName, setNewOrgName] = useState("");
  const [newOrgType, setNewOrgType] = useState("Hospital");
  const [newOrgRegion, setNewOrgRegion] = useState("");

  // New Research Request state
  const [resTitle, setResTitle] = useState("");
  const [resRequestor, setResRequestor] = useState("National Institute of Epidemiology (Synthetic)");
  const [resPurpose, setResPurpose] = useState("");

  // Settings form state
  const [dateShiftDays, setDateShiftDays] = useState(180);
  const [minGroupSize, setMinGroupSize] = useState(5);
  const [ageBandWidth, setAgeBandWidth] = useState(5);

  const fetchScopedData = useCallback(async (orgId: string, jobId: string, evtFilter: string) => {
    setLoading(true);
    setApiError(null);
    try {
      const orgQ = orgId ? `org_id=${encodeURIComponent(orgId)}` : "";
      const jobQ = jobId ? `job_id=${encodeURIComponent(jobId)}` : "";
      const scopeQ = [orgQ, jobQ].filter(Boolean).join("&");
      const scopeSuffix = scopeQ ? `?${scopeQ}` : "";
      const orgSuffix = orgQ ? `?${orgQ}` : "";

      const [
        orgsRes,
        dsRes,
        jobsRes,
        dashRes,
        identRes,
        clinRes,
        intelRes,
        atkRes,
        passRes,
        resRes,
        auditRes,
        setRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/organisations`).then((r) => r.json()),
        fetch(`${API_BASE}/datasets${orgSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/jobs${orgSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/dashboard${scopeSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/identity-graph${scopeSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/clinical-integrity${scopeSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/privacy-intelligence${scopeSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/attacks${scopeSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/passports${orgSuffix}`).then((r) => r.json()),
        fetch(`${API_BASE}/research/requests`).then((r) => r.json()),
        fetch(`${API_BASE}/audit?${[orgQ, evtFilter ? `event_type=${encodeURIComponent(evtFilter)}` : ""].filter(Boolean).join("&")}`).then((r) => r.json()),
        fetch(`${API_BASE}/settings`).then((r) => r.json()),
      ]);

      setOrganisations(orgsRes.organisations || []);
      setDatasets(dsRes.datasets || []);
      const loadedJobs = jobsRes.jobs || [];
      setJobsList(loadedJobs);
      setDashboardData(dashRes);
      setIdentityData(identRes);
      setClinicalData(clinRes);
      setIntelligenceData(intelRes);
      setAttackData(atkRes);
      setPassportsList(passRes.passports || []);
      setResearchRequests(resRes.requests || []);
      setAuditLogs(auditRes.audit_logs || []);
      setSettingsData(setRes);

      if (setRes?.parameters) {
        setDateShiftDays(setRes.parameters.date_shift_max_days ?? 180);
        setMinGroupSize(setRes.parameters.min_group_size ?? 5);
        setAgeBandWidth(setRes.parameters.age_band_width ?? 5);
      }

      const activeJId = jobId || dashRes?.latest_job?.id || "";
      if (activeJId) {
        const jd = await fetch(`${API_BASE}/jobs/${encodeURIComponent(activeJId)}`).then((r) =>
          r.ok ? r.json() : null
        );
        setJobDetail(jd?.job || null);
      } else {
        setJobDetail(null);
      }
    } catch (e: any) {
      setApiError(e?.message || "Failed to connect to local MediLocker backend API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
  }, [selectedOrgId, selectedJobId, auditEventFilter, fetchScopedData]);

  const handleOrgChange = (newOrgId: string) => {
    setSelectedOrgId(newOrgId);
    setSelectedJobId("");
    setSelectedCluster(null);
    setSelectedPassport(null);
    setPassportVerifyResult(null);
  };

  const handleUploadDataset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFiles || uploadFiles.length === 0) {
      setApiError("Please select at least one file to upload.");
      return;
    }
    setApiError(null);
    setStatusBanner("Validating and registering dataset...");
    try {
      const fd = new FormData();
      fd.append("org_id", selectedOrgId);
      fd.append("name", uploadName.trim() || `Batch_${new Date().toISOString().slice(0, 10)}`);
      Array.from(uploadFiles).forEach((f) => fd.append("files", f));
      const res = await fetch(`${API_BASE}/datasets/upload`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setSelectedDatasetId(data.dataset_id);
      setUploadName("");
      setUploadFiles(null);
      setStatusBanner(`Dataset ${data.dataset_id} registered (${data.validation_status}).`);
      await fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
      setStatusBanner(null);
    }
  };

  const handleRunEngine = async () => {
    setIsRunningJob(true);
    setApiError(null);
    setStatusBanner("Executing offline privacy engine (Pass 1, Pass 2, Attack Sim & Passport)...");
    try {
      const fd = new FormData();
      fd.append("dataset_id", selectedDatasetId);
      fd.append("org_id", selectedOrgId);
      const res = await fetch(`${API_BASE}/jobs`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Job execution failed");
      setSelectedJobId(data.job_id);
      setStatusBanner(`Job ${data.job_id} completed. Release Decision: ${data.release_decision}`);
      await fetchScopedData(selectedOrgId, data.job_id, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
      setStatusBanner(null);
    } finally {
      setIsRunningJob(false);
    }
  };

  const handleReleaseDecision = async (jobId: string, decision: "APPROVED" | "REJECTED") => {
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/release`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, reason: "Privacy Officer console review" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Release update failed");
      setStatusBanner(`Release decision updated to ${data.release_decision}`);
      await fetchScopedData(selectedOrgId, jobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const handleRunAttacks = async (jobId: string) => {
    setApiError(null);
    setStatusBanner("Running 7-vector attack simulation on sanitized output...");
    try {
      const res = await fetch(`${API_BASE}/attacks/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Attack simulation failed");
      setStatusBanner(`Attack simulation executed: ${data.vectors_blocked}/${data.vectors_total} vectors blocked.`);
      await fetchScopedData(selectedOrgId, jobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
      setStatusBanner(null);
    }
  };

  const handleInspectPassport = async (jobId: string) => {
    setApiError(null);
    setPassportVerifyResult(null);
    try {
      const res = await fetch(`${API_BASE}/passports/${encodeURIComponent(jobId)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Passport fetch failed");
      setSelectedPassport(data);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const handleVerifyPassport = async (jobId: string) => {
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE}/passports/${encodeURIComponent(jobId)}/verify`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed");
      setPassportVerifyResult(data);
      await fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrgName.trim()) return;
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE}/organisations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newOrgName, org_type: newOrgType, region: newOrgRegion || "India" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create organisation");
      setNewOrgName("");
      setNewOrgRegion("");
      setStatusBanner(`Created synthetic organisation ${data.org_id}`);
      await fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const handleCreateResearchRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resTitle.trim() || !resPurpose.trim()) return;
    setApiError(null);
    try {
      const orgName = organisations.find((o) => o.id === selectedOrgId)?.name || selectedOrgId;
      const res = await fetch(`${API_BASE}/research/requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: resTitle,
          requestor_org: resRequestor,
          target_orgs: [orgName],
          dataset_id: selectedDatasetId,
          purpose: resPurpose,
          datasets_requested: [selectedDatasetId],
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create research request");
      setResTitle("");
      setResPurpose("");
      setStatusBanner(`Research request ${data.request_id} created.`);
      await fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const handleResearchAction = async (id: string, action: "approve" | "reject") => {
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE}/research/requests/${encodeURIComponent(id)}/${action}`, { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Failed to ${action} request`);
      setStatusBanner(data.message);
      await fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date_shift_max_days: Number(dateShiftDays),
          min_group_size: Number(minGroupSize),
          age_band_width: Number(ageBandWidth),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to save settings");
      setStatusBanner(data.message);
      await fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter);
    } catch (err: any) {
      setApiError(err.message);
    }
  };

  const navItems = [
    { id: "command_centre", label: "Dashboard", icon: Activity },
    { id: "privacy_gateway", label: "Datasets & Engine", icon: Lock },
    { id: "privacy_intelligence", label: "Privacy Intelligence", icon: BarChart3 },
    { id: "attack_simulator", label: "Attack Simulator", icon: AlertTriangle },
    { id: "organisations", label: "Organisations", icon: Building2 },
    { id: "identity_graph", label: "Identity Continuity", icon: Network },
    { id: "clinical_integrity", label: "Clinical Integrity", icon: HeartPulse },
    { id: "privacy_passports", label: "Privacy Passports", icon: Award },
    { id: "research_collab", label: "Research Network", icon: Users },
    { id: "trust_audit", label: "Audit Trail", icon: FileCheck2 },
    { id: "settings", label: "Settings", icon: SettingsIcon },
  ];

  const activeJobId = selectedJobId || dashboardData?.latest_job?.id || "";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#070D18] text-slate-100">
      {/* Sidebar */}
      <aside className="w-64 flex-shrink-0 border-r border-slate-800/80 bg-[#0B132B]/70 flex flex-col justify-between">
        <div className="overflow-y-auto">
          <div className="p-5 border-b border-slate-800/60 flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-bold text-sm tracking-wider text-white">MEDILOCKER</div>
              <div className="text-[10px] tracking-widest text-cyan-400 font-mono">GUPTKAVACH FIREWALL</div>
            </div>
          </div>

          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md text-xs font-medium transition-all ${
                    isActive
                      ? "bg-cyan-500/15 text-cyan-300 border-l-2 border-cyan-400 font-semibold"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? "text-cyan-400" : "text-slate-500"}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-4 border-t border-slate-800/60 bg-[#070D18]/60 text-[11px]">
          <div className="flex items-center justify-between text-slate-400 mb-1.5">
            <span className="flex items-center space-x-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
              <span className="font-mono text-emerald-400">OFFLINE CPU-ONLY</span>
            </span>
          </div>
          <div className="text-slate-500 font-mono truncate">Org: {selectedOrgId}</div>
          <div className="text-slate-500 font-mono truncate">Job: {activeJobId || "NONE"}</div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <header className="h-14 border-b border-slate-800/80 bg-[#0B132B]/40 px-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center space-x-3">
            <h1 className="text-base font-semibold text-white">
              {navItems.find((n) => n.id === activeTab)?.label}
            </h1>
            <span className="text-xs text-slate-500 font-mono">|</span>
            <select
              value={selectedOrgId}
              onChange={(e) => handleOrgChange(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-cyan-300 font-medium"
              aria-label="Select Organisation"
            >
              {organisations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs text-slate-300 font-mono"
              aria-label="Select Job"
            >
              <option value="">Latest Job ({dashboardData?.latest_job?.id || "None"})</option>
              {jobsList.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.id} ({j.release_decision})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 bg-slate-900/80 border border-slate-800 px-2.5 py-1 rounded text-xs">
              <Cpu className="h-3.5 w-3.5 text-cyan-400" />
              <span className="text-slate-400 font-mono text-[11px]">Track 3 · Zero-Internet</span>
            </div>
            <button
              onClick={() => fetchScopedData(selectedOrgId, selectedJobId, auditEventFilter)}
              className="p-1.5 text-slate-400 hover:text-cyan-300 rounded border border-slate-800"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6 bg-[#070D18] space-y-5">
          {apiError && (
            <div className="max-w-7xl mx-auto p-3 rounded bg-red-950/40 border border-red-500/40 text-xs text-red-300 flex items-center justify-between">
              <span>{apiError}</span>
              <button onClick={() => setApiError(null)} className="text-red-400 hover:text-white">Dismiss</button>
            </div>
          )}
          {statusBanner && (
            <div className="max-w-7xl mx-auto p-3 rounded bg-cyan-950/40 border border-cyan-500/40 text-xs text-cyan-300 flex items-center justify-between">
              <span>{statusBanner}</span>
              <button onClick={() => setStatusBanner(null)} className="text-cyan-400 hover:text-white">Dismiss</button>
            </div>
          )}

          {/* 1. DASHBOARD */}
          {activeTab === "command_centre" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              {!dashboardData?.has_data ? (
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-8 text-center space-y-3">
                  <Database className="h-8 w-8 text-cyan-400 mx-auto" />
                  <h2 className="text-base font-semibold text-white">No Processing Jobs Yet for This Organisation</h2>
                  <p className="text-xs text-slate-400 max-w-md mx-auto">
                    Upload a synthetic dataset or run the official practice cohort in Datasets &amp; Engine to generate real metrics.
                  </p>
                  <button
                    onClick={() => setActiveTab("privacy_gateway")}
                    className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold rounded text-xs"
                  >
                    Go to Datasets &amp; Engine
                  </button>
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-[#0B132B]/70 border border-cyan-500/20 rounded-lg p-4">
                      <div className="text-xs text-slate-400">RELEASE READINESS</div>
                      <div className="mt-2 text-xl font-bold text-white">{dashboardData.summary.release_readiness}</div>
                      <div className="mt-1 text-xs text-slate-400 font-mono">Job: {dashboardData.latest_job?.id}</div>
                    </div>
                    <div className="bg-[#0B132B]/70 border border-cyan-500/20 rounded-lg p-4">
                      <div className="text-xs text-slate-400">FILES PROCESSED</div>
                      <div className="mt-2 text-xl font-bold text-white">{dashboardData.summary.files_processed}</div>
                      <div className="mt-1 text-xs">
                        <span className="text-emerald-400">{dashboardData.summary.files_sanitized} Sanitised</span>
                        <span className="text-slate-500"> · </span>
                        <span className="text-amber-400">{dashboardData.summary.files_quarantined} Quarantined</span>
                      </div>
                    </div>
                    <div className="bg-[#0B132B]/70 border border-cyan-500/20 rounded-lg p-4">
                      <div className="text-xs text-slate-400">RECORDS &amp; PII DETECTED</div>
                      <div className="mt-2 text-xl font-bold text-white">{dashboardData.summary.records_processed} Records</div>
                      <div className="mt-1 text-xs text-cyan-400">{dashboardData.summary.identifiers_detected} PII tokens masked</div>
                    </div>
                    <div className="bg-[#0B132B]/70 border border-cyan-500/20 rounded-lg p-4">
                      <div className="text-xs text-slate-400">CRITICAL / HIGH RISKS</div>
                      <div className="mt-2 text-xl font-bold text-white">{dashboardData.summary.critical_risks}</div>
                      <div className="mt-1 text-xs text-slate-400">Pending checks: {dashboardData.summary.pending_checks}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">CLINICAL PRESERVATION</div>
                      <div className="text-sm font-semibold text-white mt-1">{dashboardData.summary.clinical_preservation}</div>
                    </div>
                    <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">IDENTITY PRECISION (GT)</div>
                      <div className="text-sm font-semibold text-amber-300 mt-1">{dashboardData.summary.identity_precision}</div>
                    </div>
                    <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">CANARY TEST STATUS</div>
                      <div className="text-sm font-semibold text-amber-300 mt-1">{dashboardData.summary.canary_status}</div>
                    </div>
                  </div>
                </>
              )}

              <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5">
                <h3 className="text-sm font-semibold text-white mb-3">Recent Processing Jobs ({selectedOrgId})</h3>
                {dashboardData?.recent_jobs?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="pb-2">JOB ID</th>
                          <th className="pb-2">DATASET</th>
                          <th className="pb-2">FILES</th>
                          <th className="pb-2">RECORDS</th>
                          <th className="pb-2">RELEASE</th>
                          <th className="pb-2 text-right">BUNDLE</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {dashboardData.recent_jobs.map((job: any) => (
                          <tr key={job.id}>
                            <td className="py-2 font-mono text-cyan-400">{job.id}</td>
                            <td className="py-2">{job.input_name}</td>
                            <td className="py-2">{job.files_sanitized}/{job.files_total}</td>
                            <td className="py-2">{job.records_processed}</td>
                            <td className="py-2 font-mono">{job.release_decision}</td>
                            <td className="py-2 text-right">
                              {job.release_decision === "APPROVED" ? (
                                <a href={`${API_BASE}/jobs/${job.id}/download`} className="text-cyan-400 hover:underline">
                                  Download ZIP
                                </a>
                              ) : (
                                <span className="text-slate-500">Locked</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-slate-500">No jobs recorded for this organisation.</p>
                )}
              </div>
            </div>
          )}

          {/* 2. DATASETS & ENGINE */}
          {activeTab === "privacy_gateway" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <form onSubmit={handleUploadDataset} className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-5 space-y-3">
                  <h2 className="text-sm font-bold text-white flex items-center space-x-2">
                    <Upload className="h-4 w-4 text-cyan-400" />
                    <span>1. Upload &amp; Validate Dataset ({selectedOrgId})</span>
                  </h2>
                  <input
                    type="text"
                    placeholder="Dataset Name (e.g. Hospital A OPD Batch)"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs text-white"
                  />
                  <input
                    type="file"
                    multiple
                    onChange={(e) => setUploadFiles(e.target.files)}
                    className="w-full text-xs text-slate-300 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-slate-800 file:text-cyan-300"
                  />
                  <button type="submit" className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded text-xs font-semibold">
                    Validate &amp; Register Dataset
                  </button>
                </form>

                <div className="bg-[#0B132B]/60 border border-cyan-500/30 rounded-lg p-5 space-y-3">
                  <h2 className="text-sm font-bold text-white flex items-center space-x-2">
                    <Lock className="h-4 w-4 text-cyan-400" />
                    <span>2. Execute Privacy Engine</span>
                  </h2>
                  <select
                    value={selectedDatasetId}
                    onChange={(e) => setSelectedDatasetId(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-xs text-white"
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.files_count} files · {d.validation_status})
                      </option>
                    ))}
                  </select>
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={handleRunEngine}
                      disabled={isRunningJob}
                      className="flex items-center space-x-2 px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded text-xs font-semibold disabled:opacity-50"
                    >
                      <Play className="h-4 w-4" />
                      <span>{isRunningJob ? "Processing..." : "Run Privacy Pipeline"}</span>
                    </button>
                    {jobDetail?.release_decision === "APPROVED" && (
                      <a
                        href={`${API_BASE}/jobs/${jobDetail.id}/download`}
                        className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold"
                      >
                        <Download className="h-4 w-4" />
                        <span>Download Bundle</span>
                      </a>
                    )}
                  </div>
                </div>
              </div>

              {jobDetail && (
                <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-white">Job Report: {jobDetail.id}</h3>
                      <p className="text-xs text-slate-400">
                        Sanitised: {jobDetail.files_sanitized} · Quarantined: {jobDetail.files_quarantined} · Release: {jobDetail.release_decision}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleReleaseDecision(jobDetail.id, "APPROVED")}
                        className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs"
                      >
                        Approve Release
                      </button>
                      <button
                        onClick={() => handleReleaseDecision(jobDetail.id, "REJECTED")}
                        className="px-3 py-1 bg-red-600 hover:bg-red-500 text-white rounded text-xs"
                      >
                        Reject Release
                      </button>
                    </div>
                  </div>

                  <div className="overflow-x-auto max-h-72 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="pb-2">INPUT SHA-256</th>
                          <th className="pb-2">STATUS</th>
                          <th className="pb-2">OUTPUT / REASON</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                        {(jobDetail.files_report || []).slice(0, 100).map((fr: any, i: number) => (
                          <tr key={i}>
                            <td className="py-1.5 text-slate-400">{(fr.input_sha256 || "").slice(0, 16)}...</td>
                            <td className="py-1.5">
                              <span className={fr.status === "sanitized" ? "text-emerald-400" : "text-amber-400"}>
                                {fr.status}
                              </span>
                            </td>
                            <td className="py-1.5 text-slate-300">{fr.output || fr.reason || "N/A"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 3. PRIVACY INTELLIGENCE */}
          {activeTab === "privacy_intelligence" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              {intelligenceData?.status !== "MEASURED" ? (
                <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-6 text-xs text-slate-400">
                  No executed job found for this filter. Run a dataset job first.
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">IDENTIFIERS DETECTED</div>
                      <div className="text-xl font-bold text-cyan-400 mt-1">{intelligenceData.measured_metrics.identifiers_detected}</div>
                    </div>
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">GENERALIZED / SUPPRESSED</div>
                      <div className="text-xl font-bold text-white mt-1">
                        {intelligenceData.measured_metrics.records_generalized} / {intelligenceData.measured_metrics.records_suppressed}
                      </div>
                    </div>
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">RARE GROUP RATE (POST)</div>
                      <div className="text-xl font-bold text-emerald-400 mt-1">{intelligenceData.measured_metrics.rare_group_rate_pct}%</div>
                    </div>
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">RESIDUAL PII LEAKAGE (GT)</div>
                      <div className="text-xl font-bold text-amber-300 mt-1">{intelligenceData.ground_truth_metrics.residual_pii_leakage}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5">
                      <h3 className="text-sm font-semibold text-white mb-3">Mitigation Actions Applied</h3>
                      <div className="space-y-2 text-xs font-mono">
                        {Object.entries(intelligenceData.mitigation_actions || {}).map(([k, v]: any) => (
                          <div key={k} className="flex justify-between p-2 bg-slate-900/50 rounded">
                            <span className="text-cyan-300">{k}</span>
                            <span className="text-white">{v}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5">
                      <h3 className="text-sm font-semibold text-white mb-3">Release Gate Assessment</h3>
                      <div className="text-xs space-y-2">
                        <div>Status: <strong className="text-cyan-400">{intelligenceData.release_gate?.status}</strong></div>
                        <div>Reason Codes: <span className="font-mono text-slate-300">{(intelligenceData.release_gate?.reason_codes || []).join(", ") || "NONE"}</span></div>
                        <div className="text-slate-400">{intelligenceData.ground_truth_metrics?.note}</div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* 4. ATTACK SIMULATOR */}
          {activeTab === "attack_simulator" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-5 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-white">7-Vector Re-Identification Attack Simulator</h2>
                  <p className="text-xs text-slate-400">
                    Executes combination linkage attacks directly against sanitized outputs.
                  </p>
                </div>
                {activeJobId && (
                  <button
                    onClick={() => handleRunAttacks(activeJobId)}
                    className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded text-xs font-semibold"
                  >
                    Re-Run Attack Simulation
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                  <div className="text-xs text-slate-400">SIMULATION STATUS</div>
                  <div className="text-lg font-bold text-white mt-1">{attackData?.status || "NOT_RUN"}</div>
                </div>
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                  <div className="text-xs text-slate-400">RESIDUAL UNIQUENESS</div>
                  <div className="text-lg font-bold text-cyan-400 mt-1">
                    {attackData?.residual_uniqueness_pct !== undefined ? `${attackData.residual_uniqueness_pct}%` : "NOT_RUN"}
                  </div>
                </div>
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                  <div className="text-xs text-slate-400">VECTORS BLOCKED</div>
                  <div className="text-lg font-bold text-emerald-400 mt-1">
                    {attackData?.vectors_blocked ?? 0} / {attackData?.vectors_total ?? 7}
                  </div>
                </div>
              </div>

              <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2">VECTOR</th>
                      <th className="pb-2">QUASI-IDENTIFIERS</th>
                      <th className="pb-2">TESTED</th>
                      <th className="pb-2">AT RISK (PRE → POST)</th>
                      <th className="pb-2">RESIDUAL %</th>
                      <th className="pb-2">STATUS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {(attackData?.vectors || []).map((v: any, idx: number) => (
                      <tr key={idx}>
                        <td className="py-2.5 font-semibold text-white">{v.label || v.strategy}</td>
                        <td className="py-2.5 font-mono text-[11px] text-slate-400">{(v.quasi_identifiers || []).join(", ")}</td>
                        <td className="py-2.5 font-mono">{v.records_tested}</td>
                        <td className="py-2.5 font-mono">{v.records_at_risk_before} → {v.records_at_risk_after}</td>
                        <td className="py-2.5 font-mono">{v.residual_risk_pct}%</td>
                        <td className="py-2.5">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                              v.status === "BLOCKED"
                                ? "bg-emerald-500/15 text-emerald-400"
                                : v.status === "AT_RISK"
                                ? "bg-red-500/15 text-red-400"
                                : "bg-amber-500/15 text-amber-300"
                            }`}
                          >
                            {v.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 5. ORGANISATIONS */}
          {activeTab === "organisations" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <form onSubmit={handleCreateOrg} className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-5 grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Organisation Name</label>
                  <input
                    type="text"
                    required
                    value={newOrgName}
                    onChange={(e) => setNewOrgName(e.target.value)}
                    placeholder="e.g. City Care Hospital"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs"
                  />
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Type</label>
                  <select
                    value={newOrgType}
                    onChange={(e) => setNewOrgType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs"
                  >
                    <option value="Hospital">Hospital</option>
                    <option value="Diagnostic Lab">Diagnostic Lab</option>
                    <option value="Research Institute">Research Institute</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] text-slate-400 block mb-1">Region</label>
                  <input
                    type="text"
                    value={newOrgRegion}
                    onChange={(e) => setNewOrgRegion(e.target.value)}
                    placeholder="e.g. Pune"
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs"
                  />
                </div>
                <button type="submit" className="flex items-center justify-center space-x-1.5 px-4 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded text-xs font-semibold">
                  <Plus className="h-4 w-4" />
                  <span>Add Organisation</span>
                </button>
              </form>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {organisations.map((org) => (
                  <div key={org.id} className={`bg-[#0B132B]/60 border rounded-lg p-5 ${selectedOrgId === org.id ? "border-cyan-400" : "border-slate-800"}`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="text-sm font-semibold text-white">{org.name}</h4>
                        <span className="text-xs text-cyan-400 font-mono">{org.org_type} · {org.region}</span>
                      </div>
                      <button
                        onClick={() => handleOrgChange(org.id)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-cyan-500 hover:text-slate-950 rounded text-[11px] font-medium"
                      >
                        {selectedOrgId === org.id ? "Selected" : "Select Org"}
                      </button>
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-2 text-xs border-t border-slate-800 pt-3">
                      <div><span className="text-slate-500 block">Datasets</span><span className="font-mono">{org.datasets_count ?? 0}</span></div>
                      <div><span className="text-slate-500 block">Jobs</span><span className="font-mono">{org.jobs_count ?? 0}</span></div>
                      <div><span className="text-slate-500 block">Records</span><span className="font-mono">{org.records_contributed ?? 0}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 6. IDENTITY CONTINUITY */}
          {activeTab === "identity_graph" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-3">
                  <div className="text-[11px] text-slate-400">EVALUATED RECORDS</div>
                  <div className="text-lg font-bold text-white">{identityData?.total_records ?? 0}</div>
                </div>
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-3">
                  <div className="text-[11px] text-slate-400">PATIENT CLUSTERS</div>
                  <div className="text-lg font-bold text-cyan-400">{identityData?.pseudonymous_clusters ?? 0}</div>
                </div>
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-3">
                  <div className="text-[11px] text-slate-400">ABSTENTIONS / UNLINKED</div>
                  <div className="text-lg font-bold text-amber-300">{identityData?.abstentions ?? 0}</div>
                </div>
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-3">
                  <div className="text-[11px] text-slate-400">CROSS-HOSPITAL LINKS</div>
                  <div className="text-lg font-bold text-emerald-400">{identityData?.multi_facility_links ?? 0}</div>
                </div>
                <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-3">
                  <div className="text-[11px] text-slate-400">PRECISION (GT)</div>
                  <div className="text-lg font-bold text-slate-300">{identityData?.precision ?? "NOT_MEASURED"}</div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(identityData?.clusters || []).map((c: any, idx: number) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedCluster(c)}
                    className={`p-4 rounded-lg border cursor-pointer ${
                      selectedCluster?.pseudonym === c.pseudonym ? "bg-cyan-950/30 border-cyan-400" : "bg-[#0B132B]/50 border-slate-800"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-sm font-bold text-cyan-400">{c.pseudonym}</span>
                      <span className="text-[11px] text-slate-300">{c.linked_records} records</span>
                    </div>
                    <div className="mt-2 text-xs text-slate-400">{(c.organisations || []).join(" ↔ ")}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 7. CLINICAL INTEGRITY */}
          {activeTab === "clinical_integrity" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              {clinicalData?.status !== "MEASURED" ? (
                <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-6 text-xs text-slate-400">
                  No executed job found for clinical validation.
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">FHIR R4 BUNDLES CHECKED</div>
                      <div className="text-xl font-bold text-white mt-1">{clinicalData.fhir_bundles_checked}</div>
                      <div className="text-xs text-emerald-400 mt-1">
                        {clinicalData.fhir_validation_passed ? "Schema Valid" : "Validation Failures"}
                      </div>
                    </div>
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">FHIR RESOURCES CHECKED</div>
                      <div className="text-xl font-bold text-cyan-400 mt-1">{clinicalData.fhir_resources_checked}</div>
                    </div>
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">MEDICATION / DOSAGE TOKENS</div>
                      <div className="text-xl font-bold text-white mt-1">{clinicalData.medication_dosage_tokens_retained}</div>
                    </div>
                    <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4">
                      <div className="text-xs text-slate-400">LAB / VITAL TOKENS</div>
                      <div className="text-xl font-bold text-white mt-1">{clinicalData.lab_vital_tokens_retained}</div>
                    </div>
                  </div>
                  <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5 text-xs space-y-2">
                    <div>Expected vs Preserved Probe Count: <strong className="text-amber-300">{clinicalData.clinical_preservation_pct}</strong></div>
                    <p className="text-slate-400">{clinicalData.note}</p>
                  </div>
                </>
              )}
            </div>
          )}

          {/* 8. PRIVACY PASSPORTS */}
          {activeTab === "privacy_passports" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <div className="bg-cyan-950/20 border border-cyan-500/30 rounded-lg p-4 text-xs text-slate-300 flex items-center space-x-2">
                <Info className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                <span>Passports are deterministic local governance evidence artifacts linked to specific job manifest hashes, not external legal certifications.</span>
              </div>

              <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2">PASSPORT ID</th>
                      <th className="pb-2">JOB ID</th>
                      <th className="pb-2">DECISION</th>
                      <th className="pb-2">SIGNATURE</th>
                      <th className="pb-2">INTEGRITY</th>
                      <th className="pb-2 text-right">ACTIONS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {passportsList.map((p) => (
                      <tr key={p.passport_id}>
                        <td className="py-2 text-cyan-300">{p.passport_id}</td>
                        <td className="py-2">{p.job_id}</td>
                        <td className="py-2">{p.release_decision}</td>
                        <td className="py-2">{p.signature_status}</td>
                        <td className="py-2">{p.verification_status}</td>
                        <td className="py-2 text-right space-x-2">
                          <button onClick={() => handleInspectPassport(p.job_id)} className="text-cyan-400 hover:underline">Inspect</button>
                          <button onClick={() => handleVerifyPassport(p.job_id)} className="text-emerald-400 hover:underline">Verify</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {passportVerifyResult && (
                <div className="p-4 rounded bg-slate-900 border border-slate-700 text-xs space-y-1">
                  <div className="font-bold text-white">Verification Result: {passportVerifyResult.status}</div>
                  <div className="text-slate-400">{(passportVerifyResult.details || []).join(" · ")}</div>
                </div>
              )}

              {selectedPassport && (
                <div className="bg-[#0B132B]/70 border border-cyan-500/30 rounded-lg p-5 space-y-2 text-xs">
                  <div className="font-bold text-white">Passport Payload ({selectedPassport.passport_id})</div>
                  <div className="text-slate-400">Output Manifest Root Hash: <span className="font-mono text-cyan-300">{selectedPassport.output_manifest_hash}</span></div>
                  <pre className="bg-slate-950 p-3 rounded text-[11px] font-mono text-slate-300 max-h-64 overflow-y-auto">
                    {JSON.stringify(selectedPassport.passport, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* 9. RESEARCH NETWORK */}
          {activeTab === "research_collab" && (
            <div className="space-y-6 max-w-7xl mx-auto">
              <form onSubmit={handleCreateResearchRequest} className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-5 space-y-3">
                <h3 className="text-sm font-semibold text-white">Create Synthetic Research Access Request</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <input
                    type="text"
                    required
                    placeholder="Study Title"
                    value={resTitle}
                    onChange={(e) => setResTitle(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs"
                  />
                  <input
                    type="text"
                    required
                    placeholder="Requesting Synthetic Institute"
                    value={resRequestor}
                    onChange={(e) => setResRequestor(e.target.value)}
                    className="bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs"
                  />
                </div>
                <input
                  type="text"
                  required
                  placeholder="Research Purpose"
                  value={resPurpose}
                  onChange={(e) => setResPurpose(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs"
                />
                <button type="submit" className="px-4 py-1.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded text-xs font-semibold">
                  Submit Request
                </button>
              </form>

              <div className="space-y-3">
                {researchRequests.map((req) => (
                  <div key={req.id} className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-4 flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="text-sm font-semibold text-white">{req.title} <span className="text-xs font-mono text-cyan-400">({req.id})</span></div>
                      <div className="text-xs text-slate-400">{req.purpose}</div>
                      <div className="text-[11px] text-slate-500">Requestor: {req.requestor_org} · Status: {req.status}</div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {req.status === "Pending" && (
                        <>
                          <button onClick={() => handleResearchAction(req.id, "approve")} className="px-3 py-1 bg-emerald-600 text-white rounded text-xs">Approve</button>
                          <button onClick={() => handleResearchAction(req.id, "reject")} className="px-3 py-1 bg-red-600 text-white rounded text-xs">Reject</button>
                        </>
                      )}
                      {req.status === "Approved" && req.permitted_output_ref && (
                        <a href={`http://127.0.0.1:8000${req.permitted_output_ref}`} className="px-3 py-1 bg-cyan-600 text-white rounded text-xs">
                          Download Approved Output
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 10. AUDIT TRAIL */}
          {activeTab === "trust_audit" && (
            <div className="space-y-4 max-w-7xl mx-auto">
              <div className="flex items-center justify-between">
                <div className="text-xs text-slate-400">Append-only audit trail (zero raw PII, zero secrets).</div>
                <select
                  value={auditEventFilter}
                  onChange={(e) => setAuditEventFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-700 rounded px-2.5 py-1 text-xs"
                >
                  <option value="">All Event Types</option>
                  <option value="DATASET_UPLOAD_AND_VALIDATION">Dataset Upload</option>
                  <option value="PROCESSING_COMPLETED">Processing Completed</option>
                  <option value="QUARANTINE_ENFORCED">Quarantine</option>
                  <option value="ATTACK_SIMULATION">Attack Simulation</option>
                  <option value="PASSPORT_VERIFIED">Passport Verified</option>
                  <option value="RELEASE_APPROVED">Release Approved</option>
                  <option value="BUNDLE_DOWNLOAD">Bundle Download</option>
                  <option value="SETTINGS_UPDATED">Settings Updated</option>
                </select>
              </div>
              <div className="bg-[#0B132B]/50 border border-slate-800 rounded-lg p-5 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400">
                      <th className="pb-2">TIMESTAMP</th>
                      <th className="pb-2">EVENT</th>
                      <th className="pb-2">ORG / JOB</th>
                      <th className="pb-2">DESCRIPTION</th>
                      <th className="pb-2">STATUS</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-[11px]">
                    {auditLogs.map((log) => (
                      <tr key={log.id}>
                        <td className="py-2 text-slate-400">{new Date(log.timestamp * 1000).toLocaleString()}</td>
                        <td className="py-2 font-mono text-cyan-300">{log.event_type}</td>
                        <td className="py-2 font-mono text-slate-400">{log.org_id || "-"} / {log.job_id || "-"}</td>
                        <td className="py-2 text-slate-300">{log.description}</td>
                        <td className="py-2 font-mono text-emerald-400">{log.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 11. SETTINGS */}
          {activeTab === "settings" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-7xl mx-auto">
              <form onSubmit={handleSaveSettings} className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-5 space-y-4">
                <h3 className="text-sm font-semibold text-white">Local Privacy Policy Parameters</h3>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Date Shift Max Days (1–365)</label>
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={dateShiftDays}
                    onChange={(e) => setDateShiftDays(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Minimum Group Size k (2–50)</label>
                  <input
                    type="number"
                    min={2}
                    max={50}
                    value={minGroupSize}
                    onChange={(e) => setMinGroupSize(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Age Band Width (1–20)</label>
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={ageBandWidth}
                    onChange={(e) => setAgeBandWidth(Number(e.target.value))}
                    className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-1.5 text-xs font-mono"
                  />
                </div>
                <button type="submit" className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 rounded text-xs font-semibold">
                  Save &amp; Sync Policy
                </button>
              </form>

              <div className="bg-[#0B132B]/60 border border-slate-800 rounded-lg p-5 space-y-3 text-xs">
                <h3 className="text-sm font-semibold text-white">Security &amp; Runtime Status</h3>
                <div>Secret Status: <strong className="text-cyan-300">{settingsData?.security_status?.secret_source}</strong></div>
                <div>Encryption at Rest: <strong className="text-emerald-400">{settingsData?.security_status?.encryption_at_rest}</strong></div>
                <div>Offline Mode: <strong className="text-emerald-400">{settingsData?.security_status?.offline_mode ? "Enabled (Zero Internet)" : "Disabled"}</strong></div>
                <div>App Version: <span className="font-mono">{settingsData?.security_status?.app_version}</span></div>
                <pre className="bg-slate-950 p-3 rounded text-[11px] font-mono text-cyan-300 border border-slate-800">
                  {settingsData?.policy_content || ""}
                </pre>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

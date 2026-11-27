"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type ClinicalReport,
  type JobRecord,
  type Organisation,
  type Passport,
  type PrivacyAssessment,
  type ThreatLabData,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { InfoTerm } from "@/components/ui/InfoTerm";
import { ConfirmationDialog, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import {
  Upload,
  FolderOpen,
  Shield,
  HeartPulse,
  CheckCircle2,
  Download,
  FileText,
  Lock,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Swords,
} from "lucide-react";

const SUPPORTED_EXTS = new Set([".csv", ".tsv", ".json", ".jsonl", ".txt"]);
const QUARANTINE_TEST_EXTS = new Set([".pdf", ".png"]);
const MAX_UPLOAD_MB = 100;

const STEPS = [
  { id: 1, title: "Upload Data" },
  { id: 2, title: "Protect Identities" },
  { id: 3, title: "Medical Check" },
  { id: 4, title: "Test Protection" },
  { id: 5, title: "Download" },
];

export default function ProtectDataPage() {
  const [step, setStep] = useState(1);
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [selectedOrg, setSelectedOrg] = useState("");
  const [datasetName, setDatasetName] = useState("");
  const [syntheticConfirmed, setSyntheticConfirmed] = useState(true);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const [job, setJob] = useState<JobRecord | null>(null);
  const [privacy, setPrivacy] = useState<PrivacyAssessment | null>(null);
  const [clinical, setClinical] = useState<ClinicalReport | null>(null);
  const [identity, setIdentity] = useState<Record<string, unknown> | null>(null);
  const [passport, setPassport] = useState<Passport | null>(null);
  const [threatLab, setThreatLab] = useState<ThreatLabData | null>(null);

  const [showAdvancedHow, setShowAdvancedHow] = useState(false);
  const [runningAttack, setRunningAttack] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [confirmMappingOpen, setConfirmMappingOpen] = useState(false);
  const [judgeMode, setJudgeMode] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .authConfig()
      .then((c) => setJudgeMode(Boolean(c.judge_mode)))
      .catch(() => {});
    api
      .organisations()
      .then((list) => {
        setOrgs(list);
        if (list.length > 0 && !selectedOrg) setSelectedOrg(list[0].id);
      })
      .catch(() => {});
  }, []);

  async function refreshResults(jobId: string) {
    try {
      const [res, tl] = await Promise.all([
        api.jobResults(jobId),
        api.threatLab().catch(() => null),
      ]);
      setJob(res.job);
      setPrivacy(res.privacy_assessment);
      setClinical(res.clinical_report);
      setIdentity(res.identity_cluster);
      setPassport(res.passport);
      if (tl) setThreatLab(tl);
    } catch {
      // ignore transient polling error
    }
  }

  useEffect(() => {
    if (!job) return;
    const terminal = ["COMPLETED", "COMPLETED_WITH_WARNINGS", "QUARANTINED", "BLOCKED", "FAILED", "CANCELLED"];
    if (terminal.includes(job.status)) {
      const t = setTimeout(() => {
        void refreshResults(job.id);
      }, 0);
      return () => clearTimeout(t);
    }
    const timer = setInterval(async () => {
      try {
        const updated = await api.getJob(job.id);
        setJob(updated);
        if (terminal.includes(updated.status)) {
          clearInterval(timer);
          await refreshResults(updated.id);
        }
      } catch {
        clearInterval(timer);
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [job?.id, job?.status]);

  const fileSummary = useMemo(() => {
    const seen = new Set<string>();
    const duplicates: string[] = [];
    const unsupported: string[] = [];
    const formats = new Set<string>();
    let totalBytes = 0;

    for (const f of selectedFiles) {
      totalBytes += f.size;
      const key = `${f.name}:${f.size}`;
      if (seen.has(key)) duplicates.push(f.name);
      seen.add(key);

      const dot = f.name.lastIndexOf(".");
      const ext = dot >= 0 ? f.name.slice(dot).toLowerCase() : "";
      if (SUPPORTED_EXTS.has(ext)) {
        formats.add(ext.slice(1).toUpperCase());
      } else if (QUARANTINE_TEST_EXTS.has(ext)) {
        unsupported.push(`${f.name} (will be quarantined safely)`);
      } else {
        unsupported.push(`${f.name} (unsupported format)`);
      }
    }
    return {
      totalFiles: selectedFiles.length,
      formats: Array.from(formats),
      duplicates,
      unsupported,
      totalMb: (totalBytes / (1024 * 1024)).toFixed(2),
    };
  }, [selectedFiles]);

  function addFiles(list: FileList | null) {
    if (!list) return;
    setSelectedFiles((prev) => [...prev, ...Array.from(list)]);
  }

  async function handleStartProtection() {
    if (selectedFiles.length === 0) {
      setError("Please select at least one file to continue.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const fd = new FormData();
      if (selectedOrg) fd.append("organisation_id", selectedOrg);
      if (datasetName.trim()) fd.append("name", datasetName.trim());
      fd.append("auto_process", "true");
      for (const f of selectedFiles) fd.append("files", f);
      const res = await api.uploadDataset(fd);
      if (res.job) {
        setJob(res.job);
        setStep(2);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setUploading(false);
    }
  }

  async function handleRunAttack() {
    if (!job) return;
    setRunningAttack(true);
    setError("");
    try {
      await api.runAttackSimulator(job.id);
      await refreshResults(job.id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunningAttack(false);
    }
  }

  async function handleDownloadPdf() {
    if (!job) return;
    setDownloadingPdf(true);
    setError("");
    try {
      const blob = await api.downloadPrivacyReportPdf(job.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `MediLocker_Privacy_Integrity_Report_${job.id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloadingPdf(false);
    }
  }

  const clinDetails = useMemo(() => {
    if (!clinical?.details_json) return null;
    try {
      return JSON.parse(clinical.details_json) as {
        categories?: Record<string, { expected?: number; preserved?: number; modified?: number; missing?: number }>;
      };
    } catch {
      return null;
    }
  }, [clinical]);

  const latestAttackForJob = useMemo(() => {
    if (!threatLab?.history || !job) return null;
    return threatLab.history.find((r) => r.job_id === job.id) || threatLab.history[0] || null;
  }, [threatLab, job]);

  const releaseReady =
    job &&
    ["APPROVED", "APPROVED_WITH_WARNINGS"].includes(job.release_decision || "") &&
    ["COMPLETED", "COMPLETED_WITH_WARNINGS"].includes(job.status);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="GUIDED WORKFLOW · PROTECT DATA"
        title="Protect Healthcare Data"
        subtitle="A five-step guided workspace to remove patient-identifying information while keeping medical values intact."
      />

      {/* Stepper Bar */}
      <nav aria-label="Protect Data Steps" className="bg-white border border-[#DADADA] rounded-2xl p-3">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {STEPS.map((s) => {
            const active = step === s.id;
            const enabled = s.id === 1 || job !== null;
            return (
              <button
                key={s.id}
                type="button"
                disabled={!enabled}
                onClick={() => enabled && setStep(s.id)}
                className={`px-3 py-2.5 rounded-xl text-left transition-colors border ${
                  active
                    ? "bg-[#090909] text-white border-[#090909]"
                    : enabled
                    ? "bg-[#F4F4F2] text-[#090909] border-[#E5E5E5] hover:border-[#090909]"
                    : "bg-white text-[#888888] border-[#E5E5E5] opacity-55 cursor-not-allowed"
                }`}
              >
                <div className="text-[10px] font-semibold uppercase tracking-[0.08em] opacity-75">
                  Step 0{s.id}
                </div>
                <div className="text-[12.5px] font-semibold truncate">{s.title}</div>
              </button>
            );
          })}
        </div>
      </nav>

      {error && <ErrorState message={error} />}

      {/* STEP 1 — UPLOAD HEALTHCARE DATA */}
      {step === 1 && (
        <section className="bg-white border border-[#DADADA] rounded-2xl p-6 sm:p-8 space-y-6">
          <div>
            <h2 className="font-serif-display text-[26px] text-[#090909]">
              Bring your healthcare data
            </h2>
            <p className="text-[13.5px] text-[#666666] mt-1">
              Upload patient records from your hospital or research environment. MediLocker will inspect supported files before processing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-semibold uppercase tracking-[0.05em] text-[#666666] mb-1.5">
                Dataset Name
              </label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="e.g. Ward B Synthetic Discharge Batch"
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#DADADA] text-[13.5px] text-[#090909] focus:outline-none focus:border-[#090909]"
              />
            </div>
            <div>
              <label className="block text-[12px] font-semibold uppercase tracking-[0.05em] text-[#666666] mb-1.5">
                Organisation / Source (Optional)
              </label>
              <select
                value={selectedOrg}
                onChange={(e) => setSelectedOrg(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl border border-[#DADADA] bg-white text-[13.5px] text-[#090909] focus:outline-none focus:border-[#090909]"
              >
                {orgs.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className="inline-flex items-center gap-2 text-[13px] text-[#090909] cursor-pointer">
            <input
              type="checkbox"
              checked={syntheticConfirmed}
              onChange={(e) => setSyntheticConfirmed(e.target.checked)}
              className="rounded border-[#DADADA]"
            />
            <span>Synthetic or authorised evaluation dataset (no unapproved real patient data)</span>
          </label>

          {/* Dropzone */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              addFiles(e.dataTransfer.files);
            }}
            className={`border border-dashed rounded-2xl p-8 text-center transition-colors ${
              dragActive ? "border-[#090909] bg-[#F4F4F2]" : "border-[#DADADA] bg-[#FAFAFA]"
            }`}
          >
            <Upload size={22} className="mx-auto text-[#090909] mb-3" />
            <div className="text-[14px] font-semibold text-[#090909]">
              Drag and drop healthcare files here
            </div>
            <p className="text-[12.5px] text-[#666666] mt-1 max-w-xl mx-auto">
              Accepted formats: CSV, TSV, JSON, Nested JSON, FHIR R4 JSON, JSONL, TXT (discharge summaries, prescriptions, nursing notes). Max {MAX_UPLOAD_MB} MB per upload. Unsupported files (such as PDF/PNG) are quarantined safely.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222]"
              >
                Browse files
              </button>
              <button
                type="button"
                onClick={() => folderInputRef.current?.click()}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white border border-[#DADADA] text-[#090909] text-[13px] font-medium hover:bg-[#F4F4F2]"
              >
                <FolderOpen size={14} />
                <span>Browse folder</span>
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".csv,.tsv,.json,.jsonl,.txt,.pdf,.png"
              onChange={(e) => addFiles(e.target.files)}
              className="hidden"
            />
            <input
              ref={folderInputRef}
              type="file"
              // @ts-expect-error webkitdirectory is supported in Chromium/Edge browsers
              webkitdirectory=""
              multiple
              onChange={(e) => addFiles(e.target.files)}
              className="hidden"
            />
          </div>

          {selectedFiles.length > 0 && (
            <div className="bg-[#F4F4F2] border border-[#DADADA] rounded-2xl p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-[13.5px] font-semibold text-[#090909]">
                  Dataset Pre-Check Summary
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedFiles([])}
                  className="text-[12px] text-[#666666] hover:text-[#090909]"
                >
                  Clear selection
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[12.5px]">
                <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                  <div className="text-[#666666]">Total files</div>
                  <div className="text-[16px] font-bold text-[#090909]">{fileSummary.totalFiles}</div>
                </div>
                <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                  <div className="text-[#666666]">Recognised formats</div>
                  <div className="text-[14px] font-semibold text-[#090909]">
                    {fileSummary.formats.length > 0 ? fileSummary.formats.join(", ") : "None"}
                  </div>
                </div>
                <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                  <div className="text-[#666666]">Total size</div>
                  <div className="text-[16px] font-bold text-[#090909]">{fileSummary.totalMb} MB</div>
                </div>
                <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                  <div className="text-[#666666]">Files needing attention</div>
                  <div className="text-[16px] font-bold text-[#090909]">
                    {fileSummary.unsupported.length + fileSummary.duplicates.length}
                  </div>
                </div>
              </div>
              {fileSummary.duplicates.length > 0 && (
                <div className="text-[12px] text-[#7A5C00] bg-[#FFFBF0] border border-[#E6D5A0] rounded-lg px-3 py-2">
                  Duplicate files detected: {fileSummary.duplicates.join(", ")}
                </div>
              )}
              {fileSummary.unsupported.length > 0 && (
                <div className="text-[12px] text-[#7A5C00] bg-[#FFFBF0] border border-[#E6D5A0] rounded-lg px-3 py-2">
                  Attention: {fileSummary.unsupported.join(", ")}
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end">
            <button
              type="button"
              disabled={uploading || selectedFiles.length === 0 || !syntheticConfirmed}
              onClick={handleStartProtection}
              className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-[#090909] text-white text-[13.5px] font-semibold hover:bg-[#222222] disabled:opacity-50"
            >
              {uploading && <Loader2 size={15} className="animate-spin" />}
              <span>{uploading ? "Uploading & Starting…" : "Review and protect data"}</span>
            </button>
          </div>
        </section>
      )}

      {/* STEP 2 — DETECT AND PROTECT IDENTITIES */}
      {step === 2 && job && (
        <section className="bg-white border border-[#DADADA] rounded-2xl p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-serif-display text-[26px] text-[#090909]">
                Protect patient identities
              </h2>
              <p className="text-[13.5px] text-[#666666] mt-1">
                MediLocker identifies personal information (<InfoTerm term="PII" />) and replaces patient identities with consistent protected references (<InfoTerm term="Pseudonymisation" />).
              </p>
            </div>
            <StatusBadge status={job.status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              "Reading healthcare records",
              "Detecting personal information",
              "Matching patient records",
              "Protecting identifiers",
              "Reducing re-identification risk",
              "Preparing sanitised files",
            ].map((label, idx) => {
              const done = ["COMPLETED", "COMPLETED_WITH_WARNINGS", "BLOCKED", "QUARANTINED"].includes(job.status);
              return (
                <div key={label} className="p-3.5 rounded-xl bg-[#F4F4F2] border border-[#E5E5E5]">
                  <div className="text-[10.5px] font-bold text-[#666666] mb-1">0{idx + 1}</div>
                  <div className="text-[12.5px] font-medium text-[#090909]">{label}</div>
                  <div className="mt-2 text-[11px] font-semibold text-[#666666]">
                    {done ? "Completed" : "In progress…"}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Personal identifiers detected</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">
                {privacy ? privacy.pii_detected : "Not measured"}
              </div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Identifiers protected</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">
                {privacy ? Math.max(0, privacy.pii_detected - privacy.residual_leakage) : "Not measured"}
              </div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Patient records linked</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">
                {job.records_linked ?? "Not measured"}
              </div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Ambiguous matches abstained</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">
                {identity && typeof identity.abstentions === "number" ? identity.abstentions : "Not measured"}
              </div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Files quarantined</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">
                {job.files_quarantined ?? 0}
              </div>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#F4F4F2] border border-[#E5E5E5] text-[12.5px] text-[#666666]">
            <strong className="text-[#090909]">Protected categories:</strong> Patient names, family &amp; relationship references, phone numbers, addresses, Indian identity numbers (Aadhaar, ABHA, PAN), dates &amp; locations, and hospital identifiers. Raw patient records are never displayed in the browser.
          </div>

          <div className="border border-[#DADADA] rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() => setShowAdvancedHow((v) => !v)}
              className="w-full px-4 py-3 flex items-center justify-between text-[13px] font-semibold text-[#090909] bg-[#FAFAFA]"
            >
              <span>How MediLocker protects identities (technical details)</span>
              {showAdvancedHow ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>
            {showAdvancedHow && (
              <div className="p-4 text-[12.5px] text-[#666666] space-y-1.5 border-t border-[#E5E5E5]">
                <p>1. Offline CPU-only two-pass pipeline: Pass 1 extracts clues and builds conservative patient clusters without merging ambiguous names.</p>
                <p>2. Pass 2 derives domain-separated HKDF-SHA256 subkeys from <code>RAKSHA_SECRET</code> to generate deterministic <code>PSN-XXXXXX</code> pseudonyms and per-patient date shifts.</p>
                <p>3. Quasi-identifiers (5-year age bands, PIN prefixes, rare combinations) are generalised or suppressed under k-anonymity policy.</p>
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <button type="button" onClick={() => setStep(1)} className="px-4 py-2 rounded-lg border border-[#DADADA] text-[13px] font-medium">
              ← Back
            </button>
            <button type="button" onClick={() => setStep(3)} className="px-5 py-2.5 rounded-xl bg-[#090909] text-white text-[13px] font-semibold">
              Next: Check Medical Information →
            </button>
          </div>
        </section>
      )}

      {/* STEP 3 — CHECK MEDICAL INFORMATION */}
      {step === 3 && job && (
        <section className="bg-white border border-[#DADADA] rounded-2xl p-6 sm:p-8 space-y-6">
          <div>
            <h2 className="font-serif-display text-[26px] text-[#090909]">
              Make sure medical information stays intact
            </h2>
            <p className="text-[13.5px] text-[#666666] mt-1">
              Privacy protection should not change the clinical information (<InfoTerm term="Clinical fidelity" />) that healthcare professionals need.
            </p>
          </div>

          {clinical && (clinical.modified_values > 0 || clinical.fhir_integrity === "FAILED") && (
            <div className="p-4 rounded-xl bg-[#FDF2F2] border border-[#E5B8B8] text-[13px] text-[#7F1D1D] flex items-center gap-2.5">
              <AlertTriangle size={16} />
              <span>Clinical integrity warning: silent value modification or FHIR R4 validation failure detected. Release is blocked.</span>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Expected values</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">{clinical ? clinical.expected_values : "Not assessed"}</div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Preserved (unchanged)</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">{clinical ? clinical.preserved_values : "Not assessed"}</div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Modified (altered)</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">{clinical ? clinical.modified_values : "Not assessed"}</div>
            </div>
            <div className="p-4 rounded-xl border border-[#DADADA]">
              <div className="text-[12px] text-[#666666]">Missing (not found)</div>
              <div className="text-[22px] font-bold text-[#090909] mt-1">{clinical ? clinical.missing_values : "Not assessed"}</div>
            </div>
          </div>

          <div className="overflow-x-auto border border-[#DADADA] rounded-xl">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-[#F4F4F2] border-b border-[#E5E5E5] text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                  <th className="px-4 py-3">Medical Category</th>
                  <th className="px-4 py-3">Expected</th>
                  <th className="px-4 py-3">Preserved</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5] text-[13px]">
                {[
                  ["Medication names", "medication_names"],
                  ["Dosages", "dosages"],
                  ["Units", "units"],
                  ["Frequency & route", "frequencies"],
                  ["Vital signs", "blood_pressure"],
                  ["Laboratory values", "laboratory_measurements"],
                  ["Diagnoses", "diagnoses"],
                  ["FHIR / procedure codes", "fhir_codes"],
                ].map(([label, key]) => {
                  const cat = clinDetails?.categories?.[key];
                  const exp = cat?.expected;
                  const pres = cat?.preserved;
                  const status =
                    exp == null
                      ? "Not assessed"
                      : (cat?.modified || 0) > 0
                      ? "FAILED"
                      : pres === exp
                      ? "PASS"
                      : "WARNING";
                  return (
                    <tr key={key}>
                      <td className="px-4 py-3 font-medium text-[#090909]">{label}</td>
                      <td className="px-4 py-3 text-[#666666]">{exp ?? "Not assessed"}</td>
                      <td className="px-4 py-3 text-[#090909]">{pres ?? "Not assessed"}</td>
                      <td className="px-4 py-3"><StatusBadge status={status} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between">
            <button type="button" onClick={() => setStep(2)} className="px-4 py-2 rounded-lg border border-[#DADADA] text-[13px] font-medium">
              ← Back
            </button>
            <button type="button" onClick={() => setStep(4)} className="px-5 py-2.5 rounded-xl bg-[#090909] text-white text-[13px] font-semibold">
              Next: Test Protection →
            </button>
          </div>
        </section>
      )}

      {/* STEP 4 — TEST PRIVACY AND VERIFY RESULTS */}
      {step === 4 && job && (
        <section className="bg-white border border-[#DADADA] rounded-2xl p-6 sm:p-8 space-y-6">
          <div>
            <h2 className="font-serif-display text-[26px] text-[#090909]">
              Test how well your data is protected
            </h2>
            <p className="text-[13.5px] text-[#666666] mt-1">
              MediLocker checks whether sensitive information remains exposed after processing.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-xl border border-[#DADADA] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[14px] font-semibold text-[#090909]">A. Identity protection</span>
                <StatusBadge status={privacy ? (privacy.residual_leakage === 0 ? "PASS" : "FAILED") : "NOT_RUN"} />
              </div>
              <p className="text-[12.5px] text-[#666666]">
                {privacy
                  ? `${privacy.residual_leakage} residual direct identifier leaks detected in post-processing checks.`
                  : "Privacy assessment has not completed yet."}
              </p>
            </div>

            <div className="p-5 rounded-xl border border-[#DADADA] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[14px] font-semibold text-[#090909]">
                  B. Re-identification resistance (<InfoTerm term="Quasi-identifiers" />)
                </span>
                <StatusBadge status={privacy?.reid_risk_level || "NOT_MEASURED"} />
              </div>
              <p className="text-[12.5px] text-[#666666]">
                Checks whether combinations of rare diagnoses, visits, or age bands could single out a patient.
              </p>
            </div>

            <div className="p-5 rounded-xl border border-[#DADADA] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[14px] font-semibold text-[#090909]">C. Patient identity consistency</span>
                <StatusBadge status={identity ? (Number(identity.false_merges || 0) === 0 ? "PASS" : "WARNING") : "NOT_MEASURED"} />
              </div>
              <p className="text-[12.5px] text-[#666666]">
                <InfoTerm term="Identity precision" />: {identity?.precision != null ? Number(identity.precision).toFixed(2) : "Not measured"} ·{" "}
                <InfoTerm term="Identity recall" />: {identity?.recall != null ? Number(identity.recall).toFixed(2) : "Not measured"} · False merges:{" "}
                {identity?.false_merges != null ? String(identity.false_merges) : "Not measured"}
              </p>
            </div>

            <div className="p-5 rounded-xl border border-[#DADADA] space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[14px] font-semibold text-[#090909]">
                  D. Output &amp; <InfoTerm term="Privacy Passport" />
                </span>
                <StatusBadge status={passport ? passport.signature_status : "NOT_RUN"} />
              </div>
              <p className="text-[12.5px] text-[#666666]">
                {passport
                  ? `Passport ${passport.id} generated (${passport.signature_status}). Quarantined files: ${job.files_quarantined ?? 0}.`
                  : "Privacy Passport not yet generated."}
              </p>
            </div>
          </div>

          {/* Attack Simulation Area */}
          <div className="bg-[#F4F4F2] border border-[#DADADA] rounded-2xl p-5 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-[14.5px] font-semibold text-[#090909] flex items-center gap-2">
                  <Swords size={16} />
                  <span>Adversarial Attack Simulation</span>
                </h3>
                <p className="text-[12.5px] text-[#666666]">
                  Tests whether linkage, uniqueness, or <InfoTerm term="Canary" /> recall attacks succeed against the sanitised output.
                </p>
              </div>
              <button
                type="button"
                disabled={runningAttack}
                onClick={handleRunAttack}
                className="px-4 py-2 rounded-lg bg-[#090909] text-white text-[12.5px] font-medium hover:bg-[#222222] disabled:opacity-50"
              >
                {runningAttack ? "Running simulation…" : "Re-run Attack Simulation"}
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-[12.5px]">
              <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Attacks attempted</div>
                <div className="text-[16px] font-bold text-[#090909]">
                  {latestAttackForJob ? latestAttackForJob.total_count : "Not run"}
                </div>
              </div>
              <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Defences passed</div>
                <div className="text-[16px] font-bold text-[#090909]">
                  {latestAttackForJob ? latestAttackForJob.blocked_count : "Not run"}
                </div>
              </div>
              <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Direct PII leaks</div>
                <div className="text-[16px] font-bold text-[#090909]">
                  {privacy ? privacy.residual_leakage : "Not run"}
                </div>
              </div>
              <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Canary leaks</div>
                <div className="text-[16px] font-bold text-[#090909]">
                  {privacy ? `${privacy.canary_leaks}/${privacy.canary_planted}` : "Not run"}
                </div>
              </div>
              <div className="bg-white p-3 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Measured risk score</div>
                <div className="text-[16px] font-bold text-[#090909]">
                  {latestAttackForJob ? `${latestAttackForJob.risk_score}%` : "Not run"}
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-between">
            <button type="button" onClick={() => setStep(3)} className="px-4 py-2 rounded-lg border border-[#DADADA] text-[13px] font-medium">
              ← Back
            </button>
            <button type="button" onClick={() => setStep(5)} className="px-5 py-2.5 rounded-xl bg-[#090909] text-white text-[13px] font-semibold">
              Next: Download Protected Data →
            </button>
          </div>
        </section>
      )}

      {/* STEP 5 — DOWNLOAD PROTECTED DATA */}
      {step === 5 && job && (
        <section className="bg-white border border-[#DADADA] rounded-2xl p-6 sm:p-8 space-y-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="font-serif-display text-[26px] text-[#090909]">
                Your protected dataset is ready
              </h2>
              <p className="text-[13.5px] text-[#666666] mt-1">
                Download the sanitised healthcare dataset and its verification reports.
              </p>
            </div>
            <StatusBadge status={releaseReady ? "PASS" : job.release_decision || job.status} />
          </div>

          {!releaseReady && (
            <div className="p-4 rounded-xl bg-[#FFFBF0] border border-[#E6D5A0] text-[13px] text-[#7A5C00] flex items-center gap-2.5">
              <AlertTriangle size={16} />
              <span>
                Release is currently blocked or incomplete ({job.release_decision || job.status}). Sanitised bundle downloads remain locked until mandatory checks pass.
              </span>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="p-5 rounded-xl bg-[#F4F4F2] border border-[#DADADA] font-mono text-[12.5px] text-[#090909] space-y-1">
              <div className="font-sans text-[11px] font-semibold uppercase tracking-[0.06em] text-[#666666] mb-2">
                Official Output Structure
              </div>
              <div>output/</div>
              <div>├── sanitized/ ({job.files_sanitized ?? 0} files)</div>
              <div>├── report.json</div>
              <div>└── records.jsonl (restricted mapping)</div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-[12.5px]">
              <div className="p-3.5 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Processed files</div>
                <div className="text-[18px] font-bold text-[#090909]">{job.files_total ?? 0}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Quarantined files</div>
                <div className="text-[18px] font-bold text-[#090909]">{job.files_quarantined ?? 0}</div>
              </div>
              <div className="p-3.5 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Privacy status</div>
                <div className="mt-1"><StatusBadge status={privacy ? (privacy.residual_leakage === 0 ? "PASS" : "FAILED") : "NOT_RUN"} /></div>
              </div>
              <div className="p-3.5 rounded-xl border border-[#E5E5E5]">
                <div className="text-[#666666]">Clinical integrity</div>
                <div className="mt-1"><StatusBadge status={clinical?.fhir_integrity || "NOT_MEASURED"} /></div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <a
              href={releaseReady ? api.jobBundleUrl(job.id, false) : undefined}
              aria-disabled={!releaseReady}
              className={`inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-[13px] font-semibold ${
                releaseReady
                  ? "bg-[#090909] text-white hover:bg-[#222222]"
                  : "bg-[#E5E5E5] text-[#888888] pointer-events-none"
              }`}
            >
              <Download size={15} />
              <span>Download sanitised dataset</span>
            </a>

            <a
              href={api.jobReportJsonUrl(job.id)}
              className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white border border-[#DADADA] text-[#090909] text-[13px] font-medium hover:bg-[#F4F4F2]"
            >
              <FileText size={15} />
              <span>Download processing report (JSON)</span>
            </a>

            <button
              type="button"
              disabled={downloadingPdf}
              onClick={handleDownloadPdf}
              className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white border border-[#090909] text-[#090909] text-[13px] font-medium hover:bg-[#F4F4F2] disabled:opacity-50"
            >
              {downloadingPdf ? <Loader2 size={15} className="animate-spin" /> : <Shield size={15} />}
              <span>Generate Privacy &amp; Integrity Report (PDF)</span>
            </button>

            {passport && (
              <a
                href={api.downloadPassportUrl(passport.id, "json")}
                className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white border border-[#DADADA] text-[#090909] text-[13px] font-medium hover:bg-[#F4F4F2]"
              >
                <CheckCircle2 size={15} />
                <span>Download Privacy Passport</span>
              </a>
            )}

            <button
              type="button"
              disabled={!releaseReady || judgeMode}
              onClick={() => setConfirmMappingOpen(true)}
              className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-white border border-[#DADADA] text-[#090909] text-[13px] font-medium hover:bg-[#F4F4F2] disabled:opacity-50"
            >
              <Lock size={15} />
              <span>
                {judgeMode
                  ? "Patient mapping disabled (Local Evaluation Mode)"
                  : "Download patient mapping (Restricted)"}
              </span>
            </button>
          </div>

          <div className="flex justify-between pt-2">
            <button type="button" onClick={() => setStep(4)} className="px-4 py-2 rounded-lg border border-[#DADADA] text-[13px] font-medium">
              ← Back
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedFiles([]);
                setJob(null);
                setPrivacy(null);
                setClinical(null);
                setIdentity(null);
                setPassport(null);
                setStep(1);
              }}
              className="px-4 py-2 rounded-lg border border-[#DADADA] text-[13px] font-medium hover:bg-[#F4F4F2]"
            >
              Protect another dataset
            </button>
          </div>
        </section>
      )}

      <ConfirmationDialog
        open={confirmMappingOpen}
        title="Download restricted patient mapping file?"
        description="records.jsonl maps original file locations to pseudonymous patient IDs. Access is restricted to authorised administrators and privacy officers and is recorded in the immutable audit log."
        confirmLabel="Download Mapping"
        onConfirm={() => {
          setConfirmMappingOpen(false);
          if (job) window.location.href = api.jobMappingUrl(job.id);
        }}
        onCancel={() => setConfirmMappingOpen(false)}
      />
    </div>
  );
}

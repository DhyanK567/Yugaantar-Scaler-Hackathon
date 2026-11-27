"use client";

import { useEffect, useState } from "react";
import {
  api,
  type ClinicalReport,
  type DashboardOverview,
  type JobRecord,
  type PrivacyIntelligence,
  type ThreatLabData,
} from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { InfoTerm } from "@/components/ui/InfoTerm";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { FileText, Loader2, Shield, HeartPulse, Users, CheckCircle2, Clock } from "lucide-react";

export default function ReportsPage() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [dash, setDash] = useState<DashboardOverview | null>(null);
  const [pi, setPi] = useState<PrivacyIntelligence | null>(null);
  const [clin, setClin] = useState<ClinicalReport[]>([]);
  const [tl, setTl] = useState<ThreatLabData | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingJobId, setDownloadingJobId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.jobs().catch(() => []),
      api.dashboard().catch(() => null),
      api.privacyIntelligence().catch(() => null),
      api.clinicalReports().catch(() => []),
      api.threatLab().catch(() => null),
    ])
      .then(([j, d, p, c, t]) => {
        setJobs(j);
        setDash(d);
        setPi(p);
        setClin(c);
        setTl(t);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function handleDownloadPdf(jobId: string) {
    setDownloadingJobId(jobId);
    setError("");
    try {
      const blob = await api.downloadPrivacyReportPdf(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `MediLocker_Privacy_Integrity_Report_${jobId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloadingJobId(null);
    }
  }

  const latestClin = clin[0] || null;
  const latestJob = jobs[0] || null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="04 · GOVERNANCE & REPORTS"
        title="Privacy & Integrity Reports"
        subtitle="Generate 3-page clinical privacy assessment PDFs and review live dataset performance across all six Secret Wards evaluation areas."
      />

      {error && <ErrorState message={error} />}

      {loading ? (
        <LoadingState label="Loading assessment reports…" />
      ) : (
        <>
          {/* Job Reports List */}
          <section className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between">
              <h2 className="text-[15px] font-semibold text-[#090909]">
                Job Assessment Reports ({jobs.length})
              </h2>
            </div>
            {jobs.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  title="No processing jobs yet"
                  description="Run Protect Data on a synthetic dataset to generate a verifiable Privacy & Integrity Report."
                />
              </div>
            ) : (
              <div className="divide-y divide-[#E5E5E5]">
                {jobs.slice(0, 10).map((j) => (
                  <div
                    key={j.id}
                    className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                  >
                    <div>
                      <div className="text-[13.5px] font-semibold text-[#090909]">
                        {j.dataset_name || j.input_name || j.id}
                      </div>
                      <div className="text-[12px] text-[#666666] mt-0.5 flex flex-wrap items-center gap-2">
                        <span className="font-mono">{j.id}</span>
                        <StatusBadge status={j.status} />
                        <StatusBadge status={j.release_decision || "PENDING"} />
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={downloadingJobId === j.id}
                      onClick={() => handleDownloadPdf(j.id)}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#090909] text-white text-[12.5px] font-medium hover:bg-[#222222] disabled:opacity-50 shrink-0"
                    >
                      {downloadingJobId === j.id ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <FileText size={14} />
                      )}
                      <span>
                        {downloadingJobId === j.id
                          ? "Generating PDF…"
                          : "Generate Privacy & Integrity Report"}
                      </span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Six Judging Categories Alignment (Live Telemetry vs Benchmark) */}
          <section className="space-y-3">
            <div>
              <h2 className="text-[15px] font-semibold text-[#090909]">
                Live Assessment Breakdown (6 Evaluation Pillars)
              </h2>
              <p className="text-[12.5px] text-[#666666]">
                Reflects actual backend measurements from your processed jobs. Reducing re-identification risk is not a mathematical proof of impossibility against arbitrary external data.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-[#090909]">
                  <Shield size={15} />
                  <span>1. Re-identification Protection</span>
                </div>
                <p className="text-[12.5px] text-[#666666]">
                  Canary leaks: <strong className="text-[#090909]">{dash?.metrics.canary_leaks.display || "Not run"}</strong> ·{" "}
                  <InfoTerm term="Quasi-identifiers" /> risk:{" "}
                  <strong className="text-[#090909]">{pi?.reid_risk_level || "Not measured"}</strong> · Attack runs:{" "}
                  <strong className="text-[#090909]">{tl?.history.length ?? 0}</strong>
                </p>
              </div>

              <div className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-[#090909]">
                  <Shield size={15} />
                  <span>2. Personal Data Detection</span>
                </div>
                <p className="text-[12.5px] text-[#666666]">
                  <InfoTerm term="PII" /> detected: <strong className="text-[#090909]">{dash?.metrics.pii_detected.display || "Not measured"}</strong> across English, Hindi (Devanagari), and Hinglish.
                </p>
              </div>

              <div className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-[#090909]">
                  <HeartPulse size={15} />
                  <span>3. Medical Data Preservation</span>
                </div>
                <p className="text-[12.5px] text-[#666666]">
                  <InfoTerm term="Clinical fidelity" />: <strong className="text-[#090909]">{dash?.metrics.clinical_preserved.display || "Not measured"}</strong> · Modified:{" "}
                  <strong className="text-[#090909]">{latestClin ? latestClin.modified_values : "Not measured"}</strong>
                </p>
              </div>

              <div className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-[#090909]">
                  <Users size={15} />
                  <span>4. Patient Identity Consistency</span>
                </div>
                <p className="text-[12.5px] text-[#666666]">
                  <InfoTerm term="Identity precision" />: <strong className="text-[#090909]">{dash?.metrics.identity_precision.display || "Not measured"}</strong> · Prevents unsafe merges.
                </p>
              </div>

              <div className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-[#090909]">
                  <CheckCircle2 size={15} />
                  <span>5. Output Quality &amp; Validity</span>
                </div>
                <p className="text-[12.5px] text-[#666666]">
                  FHIR R4: <strong className="text-[#090909]">{latestClin?.fhir_integrity || "Not measured"}</strong> · Quarantined files:{" "}
                  <strong className="text-[#090909]">{latestJob?.files_quarantined ?? "Not measured"}</strong>
                </p>
              </div>

              <div className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-[#090909]">
                  <Clock size={15} />
                  <span>6. Speed &amp; Reliability</span>
                </div>
                <p className="text-[12.5px] text-[#666666]">
                  Latest duration:{" "}
                  <strong className="text-[#090909]">
                    {latestJob?.duration_secs != null ? `${latestJob.duration_secs.toFixed(2)}s` : "Not measured"}
                  </strong>{" "}
                  · Offline CPU-only deterministic execution.
                </p>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

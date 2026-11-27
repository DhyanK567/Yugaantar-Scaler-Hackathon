"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import { api, type DashboardOverview, type PrivacyIntelligence } from "@/lib/api";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { ReleaseReadinessPanel } from "@/components/dashboard/ReleaseReadinessPanel";
import { GettingStartedPanel } from "@/components/dashboard/GettingStartedPanel";
import { PrivacyPerformanceOverview } from "@/components/dashboard/PrivacyPerformanceOverview";
import { ProcessingWorkflow } from "@/components/dashboard/ProcessingWorkflow";
import { RecentJobsPanel } from "@/components/dashboard/RecentJobsPanel";
import { AuditEventsPanel } from "@/components/dashboard/AuditEventsPanel";
import { PrivacyTrendChart } from "@/components/charts/PrivacyTrendChart";
import { ProcessingPerformanceChart } from "@/components/charts/ProcessingPerformanceChart";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [intel, setIntel] = useState<PrivacyIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [error, setError] = useState("");

  const loadDashboard = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
      setRefreshKey((k) => k + 1);
    } else setLoading(true);
    setError("");
    try {
      const [dash, pi] = await Promise.all([
        api.dashboard(),
        api.privacyIntelligence().catch(() => null),
      ]);
      setData(dash);
      setIntel(pi);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      void loadDashboard(false);
    }, 0);
    return () => clearTimeout(id);
  }, [loadDashboard]);

  const activeOrgName = "Local Workspace";

  const hasProcessedData =
    (data?.metrics.files_processed.value ?? 0) > 0 ||
    (data?.recent_jobs.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* A. PAGE HEADER */}
      <DashboardHeader
        organisationName={activeOrgName}
        freshness={data?.freshness}
        refreshing={refreshing}
        onRefresh={() => loadDashboard(true)}
      />

      {error && (
        <div className="px-4 py-3 rounded-xl bg-[#FFFBF0] border border-[#E6D5A0] text-[13px] text-[#7A5C00] flex items-center gap-2.5">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && !data ? (
        <div className="bg-white border border-[#E6E6E6] rounded-2xl p-12 text-center text-[13.5px] text-[#666666]">
          Loading MediLocker privacy telemetry…
        </div>
      ) : (
        data && (
          <>
            {/* B. OVERALL RELEASE READINESS */}
            <ReleaseReadinessPanel health={data.privacy_health} />

            {/* C. PRIMARY GET-STARTED / OPERATIONAL ACTION */}
            <GettingStartedPanel hasProcessedData={hasProcessedData} />

            {/* D0. DATASET-AWARE PRIVACY PERFORMANCE OVERVIEW */}
            <PrivacyPerformanceOverview externalRefreshKey={refreshKey} />

            {/* D1. GRAPHICAL ANALYTICS & OPERATIONAL KPIS */}
            {(() => {
              const totalRecords = data.metrics.records_processed.value ?? 0;
              const piiDetected = intel?.total_pii_detected ?? (data.metrics.pii_detected.value ?? 0);
              const residual = intel?.total_residual_leakage ?? 0;
              const sanRate =
                piiDetected > 0
                  ? `${(((piiDetected - residual) / piiDetected) * 100).toFixed(1)}%`
                  : "Not measured";
              const totalQuarantined = data.recent_jobs.reduce(
                (acc, j) => acc + (j.files_quarantined ?? 0),
                0
              );
              const kpis = [
                { label: "Total Records Processed", value: totalRecords > 0 ? totalRecords.toLocaleString() : "0" },
                { label: "PII Entities Detected", value: piiDetected > 0 ? piiDetected.toLocaleString() : "0" },
                { label: "Sanitisation Success Rate", value: sanRate },
                { label: "Files Quarantined", value: String(totalQuarantined) },
                { label: "Clinical Preservation", value: data.metrics.clinical_preserved.display },
                { label: "Latest Job Status", value: data.privacy_health.latest_job_status || "NOT_RUN" },
              ];
              return (
                <section aria-label="Privacy Graphical Analytics" className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    {kpis.map((k) => (
                      <div key={k.label} className="bg-white border border-[#DADADA] rounded-xl p-4">
                        <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-[#666666]">
                          {k.label}
                        </div>
                        <div className="font-serif-display text-[22px] text-[#090909] mt-1 truncate">
                          {k.value}
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                    <PrivacyTrendChart
                      jobs={data.recent_jobs}
                      assessments={intel?.assessments ?? []}
                      loading={loading}
                      lastUpdated={data.freshness}
                    />
                    <ProcessingPerformanceChart
                      jobs={data.recent_jobs}
                      loading={loading}
                      lastUpdated={data.freshness}
                    />
                  </div>
                </section>
              );
            })()}

            {/* D. FOUR KEY METRICS */}
            <section aria-label="Four Key Metrics">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Link href="/dashboard/datasets" className="bg-white border border-[#DADADA] rounded-2xl p-5 hover:border-[#090909] transition-colors">
                  <div className="text-[12px] font-semibold text-[#666666]">Files protected</div>
                  <div className="font-serif-display text-[28px] text-[#090909] mt-1">{data.metrics.files_processed.display}</div>
                  <div className="text-[11.5px] text-[#888888] mt-1">{data.metrics.files_processed.description}</div>
                </Link>
                <Link href="/dashboard/privacy-intelligence" className="bg-white border border-[#DADADA] rounded-2xl p-5 hover:border-[#090909] transition-colors">
                  <div className="text-[12px] font-semibold text-[#666666]">Patient identities protected</div>
                  <div className="font-serif-display text-[28px] text-[#090909] mt-1">{data.metrics.pii_detected.display}</div>
                  <div className="text-[11.5px] text-[#888888] mt-1">{data.metrics.pii_detected.description}</div>
                </Link>
                <Link href="/dashboard/clinical-integrity" className="bg-white border border-[#DADADA] rounded-2xl p-5 hover:border-[#090909] transition-colors">
                  <div className="text-[12px] font-semibold text-[#666666]">Clinical values preserved</div>
                  <div className="font-serif-display text-[28px] text-[#090909] mt-1">{data.metrics.clinical_preserved.display}</div>
                  <div className="text-[11.5px] text-[#888888] mt-1">{data.metrics.clinical_preserved.description}</div>
                </Link>
                <Link href="/dashboard/reports" className="bg-white border border-[#DADADA] rounded-2xl p-5 hover:border-[#090909] transition-colors">
                  <div className="text-[12px] font-semibold text-[#666666]">Privacy assessments</div>
                  <div className="font-serif-display text-[28px] text-[#090909] mt-1">{data.privacy_health.overall_readiness}</div>
                  <div className="text-[11.5px] text-[#888888] mt-1">Canary leaks: {data.metrics.canary_leaks.display}</div>
                </Link>
              </div>
            </section>

            {/* E. PROCESSING WORKFLOW (6-stage visual pipeline) */}
            <ProcessingWorkflow latestJob={data.recent_jobs[0] ?? null} />

            {/* E2. ATTENTION REQUIRED (only shown when real items exist) */}
            {data.recent_jobs.some(
              (j) =>
                (j.files_quarantined ?? 0) > 0 ||
                ["BLOCKED", "FAILED", "QUARANTINED"].includes(j.status) ||
                ["QUEUED", "PROCESSING", "VALIDATING"].includes(j.status)
            ) && (
              <section className="bg-white border border-[#DADADA] rounded-2xl p-5 space-y-2">
                <h2 className="text-[14.5px] font-semibold text-[#090909]">Attention Required</h2>
                <div className="divide-y divide-[#E5E5E5]">
                  {data.recent_jobs
                    .filter(
                      (j) =>
                        (j.files_quarantined ?? 0) > 0 ||
                        ["BLOCKED", "FAILED", "QUARANTINED"].includes(j.status) ||
                        ["QUEUED", "PROCESSING", "VALIDATING"].includes(j.status)
                    )
                    .slice(0, 5)
                    .map((j) => (
                      <div key={j.id} className="py-2.5 flex items-center justify-between text-[12.5px]">
                        <span className="text-[#090909] font-medium">
                          {j.dataset_name || j.id} — {j.status}
                          {(j.files_quarantined ?? 0) > 0 ? ` (${j.files_quarantined} quarantined)` : ""}
                        </span>
                        <Link href="/dashboard/reports" className="text-[#090909] underline">
                          Inspect →
                        </Link>
                      </div>
                    ))}
                </div>
              </section>
            )}

            {/* F. RECENT JOBS (7 cols) & G. AUDIT EVENTS (5 cols) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              <div className="lg:col-span-7 min-w-0 flex flex-col">
                <RecentJobsPanel jobs={data.recent_jobs} />
              </div>
              <div className="lg:col-span-5 min-w-0 flex flex-col">
                <AuditEventsPanel events={data.audit_events} />
              </div>
            </div>
          </>
        )
      )}
    </div>
  );
}

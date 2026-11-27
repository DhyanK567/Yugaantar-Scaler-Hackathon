"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, AlertTriangle } from "lucide-react";
import { api, type DashboardMetricsSummary } from "@/lib/api";

interface PrivacyPerformanceOverviewProps {
  externalRefreshKey?: number;
}

function fmtTimestamp(ts?: number | null): string {
  if (!ts) return "Not processed";
  return new Date(ts * 1000).toLocaleString();
}

export function PrivacyPerformanceOverview({ externalRefreshKey = 0 }: PrivacyPerformanceOverviewProps) {
  const [scope, setScope] = useState<string>("latest");
  const [summary, setSummary] = useState<DashboardMetricsSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const loadMetrics = useCallback(async (selectedScope: string) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.dashboardMetricsSummary(selectedScope);
      setSummary(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadMetrics(scope);
    }, 0);
    return () => clearTimeout(timer);
  }, [loadMetrics, scope, externalRefreshKey]);

  const m = summary?.metrics;
  const jobs = summary?.available_jobs ?? [];

  // Card 1: Files protected
  const filesVal =
    m?.files_protected?.status === "MEASURED" && m.files_protected.count !== null
      ? m.files_protected.count.toLocaleString()
      : "No completed jobs";

  // Card 2: Identifiers protected
  const idsVal =
    m?.identifiers_protected?.status === "MEASURED" && m.identifiers_protected.transformed !== null
      ? m.identifiers_protected.transformed.toLocaleString()
      : "Awaiting processing";

  // Card 3: Clinical data preserved
  const clinicalValue =
    !m || m.clinical.status === "NOT_MEASURED" || m.clinical.expected <= 0 || m.clinical.preservation_percentage === null
      ? "Not assessed"
      : m.clinical.preserved === m.clinical.expected
      ? "100.0%"
      : `${m.clinical.preservation_percentage.toFixed(2)}%`;

  // Card 4: Privacy tests passed
  const pt = m?.privacy_tests;
  const testsVal =
    !pt || pt.total_executed === 0
      ? "Not tested"
      : pt.status === "BLOCKED"
      ? "Blocked"
      : `${pt.passed}/${pt.total_executed}`;

  const exec = m?.execution;

  return (
    <section aria-label="Privacy Performance Overview" className="space-y-4">
      {/* Selector & Provenance Bar */}
      <div className="bg-white border border-[#DADADA] rounded-2xl px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#666666]">
            Viewing results for:
          </span>
          <select
            aria-label="Select dataset or job scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg border border-[#DADADA] bg-[#F9F9F8] text-[13px] font-medium text-[#090909] min-w-[240px]"
          >
            <option value="latest">Latest completed job</option>
            <option value="aggregate">All completed datasets (Aggregate)</option>
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.dataset_name || "Dataset"} · {j.id} ({j.status})
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-[12px] text-[#666666]">
          {summary && summary.scope !== "EMPTY" && (
            <span>
              <strong className="text-[#090909]">{summary.dataset_name}</strong>
              {summary.job_id ? ` · ${summary.job_id}` : ""} · {fmtTimestamp(summary.processed_at)}
            </span>
          )}
          <button
            type="button"
            onClick={() => loadMetrics(scope)}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#DADADA] bg-white text-[12px] font-medium text-[#090909] hover:bg-[#F4F4F2] disabled:opacity-50"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="px-4 py-3 rounded-xl bg-[#FFFBF0] border border-[#E6D5A0] text-[12.5px] text-[#7A5C00] flex items-center gap-2">
          <AlertTriangle size={15} />
          <span>{error}</span>
        </div>
      )}

      {loading && !summary ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="rounded-2xl border border-[#DADADA] bg-white p-6 min-h-[156px] animate-pulse space-y-3">
              <div className="h-9 w-24 bg-[#EAEAEA] rounded" />
              <div className="h-4 w-32 bg-[#EAEAEA] rounded" />
              <div className="h-3 w-40 bg-[#F2F2F2] rounded" />
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Card 1: Files protected */}
            <div className="rounded-2xl border border-[#090909] bg-[#090909] text-white p-6 flex flex-col justify-between min-h-[156px]">
              <div className="font-serif-display text-[34px] sm:text-[38px] leading-[1.05] tracking-[-0.02em]">
                {filesVal}
              </div>
              <div className="mt-4">
                <div className="text-[13.5px] font-medium text-[#D4D4D4]">Files protected</div>
                <div className="text-[11.5px] text-[#8E8E8E] mt-0.5">
                  {m?.files_protected?.status === "MEASURED"
                    ? `Successfully sanitised files · ${m.files_protected.files_quarantined} quarantined`
                    : "Successfully sanitised files"}
                </div>
              </div>
            </div>

            {/* Card 2: Identifiers protected */}
            <div className="rounded-2xl border border-[#DADADA] bg-[#E6E6E6] text-[#090909] p-6 flex flex-col justify-between min-h-[156px]">
              <div className="font-serif-display text-[34px] sm:text-[38px] leading-[1.05] tracking-[-0.02em]">
                {idsVal}
              </div>
              <div className="mt-4">
                <div className="text-[13.5px] font-medium text-[#333333]">Identifiers protected</div>
                <div className="text-[11.5px] text-[#666666] mt-0.5">
                  {m?.identifiers_protected?.status === "MEASURED"
                    ? `Personal data detected and protected · ${m.identifiers_protected.remaining_leaks ?? 0} leaks`
                    : "Personal data detected and protected"}
                </div>
              </div>
            </div>

            {/* Card 3: Clinical data preserved */}
            <div className="rounded-2xl border border-[#B0B0B0] bg-[#BFBFBF] text-[#090909] p-6 flex flex-col justify-between min-h-[156px]">
              <div className="font-serif-display text-[34px] sm:text-[38px] leading-[1.05] tracking-[-0.02em]">
                {clinicalValue}
              </div>
              <div className="mt-4">
                <div className="text-[13.5px] font-medium text-[#1F1F1F]">Clinical data preserved</div>
                <div className="text-[11.5px] text-[#444444] mt-0.5">
                  {m?.clinical.status === "MEASURED" && m.clinical.expected > 0
                    ? `${m.clinical.preserved.toLocaleString()} / ${m.clinical.expected.toLocaleString()} values`
                    : "Preserved values / evaluated values"}
                </div>
              </div>
            </div>

            {/* Card 4: Privacy tests passed */}
            <div className="rounded-2xl border border-[#DADADA] bg-white text-[#090909] p-6 flex flex-col justify-between min-h-[156px]">
              <div className="font-serif-display text-[34px] sm:text-[38px] leading-[1.05] tracking-[-0.02em]">
                {testsVal}
              </div>
              <div className="mt-4">
                <div className="text-[13.5px] font-medium text-[#333333]">Privacy tests passed</div>
                <div className="text-[11.5px] text-[#666666] mt-0.5">
                  {pt && pt.total_executed > 0
                    ? `Verified privacy assessments · ${pt.failed} failed · ${pt.not_run} not run`
                    : "Verified privacy assessments"}
                </div>
              </div>
            </div>
          </div>

          {/* Additional Evaluation Information */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-[12px]">
            <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
              <span className="font-semibold text-[#090909]">Re-identification resistance: </span>
              <span className="text-[#666666]">
                Canary leaks{" "}
                <strong className="text-[#090909]">
                  {m?.canary.status === "TESTED" && m.canary.planted > 0
                    ? `${m.canary.leaked}/${m.canary.planted}`
                    : "Not tested"}
                </strong>
              </span>
            </div>
            <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
              <span className="font-semibold text-[#090909]">Multilingual PII detection: </span>
              <span className="text-[#666666]">
                Detected{" "}
                <strong className="text-[#090909]">
                  {m?.identifiers_protected?.status === "MEASURED"
                    ? m.identifiers_protected.detected.toLocaleString()
                    : "Not measured"}
                </strong>{" "}
                (EN / HI / Hinglish)
              </span>
            </div>
            <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
              <span className="font-semibold text-[#090909]">Patient identity consistency: </span>
              <span className="text-[#666666]">
                P:{" "}
                <strong className="text-[#090909]">
                  {m?.identity.precision != null ? m.identity.precision.toFixed(2) : "Not measured"}
                </strong>{" "}
                · R:{" "}
                <strong className="text-[#090909]">
                  {m?.identity.recall != null ? m.identity.recall.toFixed(2) : "Not measured"}
                </strong>{" "}
                · F0.5:{" "}
                <strong className="text-[#090909]">
                  {m?.identity.f05 != null ? m.identity.f05.toFixed(2) : "Not measured"}
                </strong>
              </span>
            </div>
            <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
              <span className="font-semibold text-[#090909]">Output validity: </span>
              <span className="text-[#666666]">
                FHIR R4 <strong className="text-[#090909]">{m?.operations?.fhir_integrity || "Not measured"}</strong>
              </span>
            </div>
            <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
              <span className="font-semibold text-[#090909]">Offline CPU-only compliance: </span>
              <span className="text-[#666666]">
                {exec ? `${exec.mode} · ${exec.device} · LLM: ${exec.llm_dependency}` : "Offline · CPU"}
              </span>
            </div>
            <div className="bg-white border border-[#E5E5E5] rounded-xl px-4 py-3">
              <span className="font-semibold text-[#090909]">Execution speed: </span>
              <span className="text-[#666666]">
                {m?.operations?.duration_secs != null ? `${m.operations.duration_secs.toFixed(2)}s` : "Not measured"} ·{" "}
                {m?.operations ? `${m.operations.records_processed.toLocaleString()} records` : "Not measured"}
              </span>
            </div>
          </div>
        </>
      )}
    </section>
  );
}

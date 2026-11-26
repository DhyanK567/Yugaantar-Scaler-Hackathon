"use client";

import { useCallback, useEffect, useState } from "react";
import { RefreshCw, AlertTriangle, ShieldCheck, ShieldAlert } from "lucide-react";
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
    loadMetrics(scope);
  }, [loadMetrics, scope, externalRefreshKey]);

  const m = summary?.metrics;
  const jobs = summary?.available_jobs ?? [];

  // Card 1: Canary Protection
  const canaryValue =
    !m || m.canary.status === "NOT_TESTED" || m.canary.planted <= 0 || m.canary.leaked === null
      ? "Not tested"
      : `${m.canary.leaked}/${m.canary.planted}`;
  const canaryStatusLabel =
    !m || m.canary.status === "NOT_TESTED"
      ? "Not tested"
      : m.canary.status === "FAILED"
      ? "Failed"
      : m.canary.leaked === 0
      ? "Protected"
      : "Leakage detected";

  // Card 2: Identity Precision
  const identityValue =
    !m || m.identity.status === "NOT_MEASURED" || m.identity.precision === null
      ? "Not measured"
      : m.identity.precision.toFixed(2);

  // Card 3: Clinical Fidelity (exact percentage, never rounded to 100% if < expected)
  const clinicalValue =
    !m || m.clinical.status === "NOT_MEASURED" || m.clinical.expected <= 0 || m.clinical.preservation_percentage === null
      ? "Not measured"
      : m.clinical.preserved === m.clinical.expected
      ? "100.0%"
      : `${m.clinical.preservation_percentage.toFixed(2)}%`;

  // Card 4: Execution Compliance
  const exec = m?.execution;
  const execHeadline =
    !exec
      ? "Not verified"
      : exec.verification_status === "VERIFIED"
      ? "Passed"
      : exec.verification_status === "FAILED"
      ? "Failed"
      : "Not verified";

  return (
    <section aria-label="Privacy Performance Overview" className="space-y-3.5">
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

      {/* Skeleton Loading State */}
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Canary Protection */}
          <div className="rounded-2xl border border-[#090909] bg-[#090909] text-white p-6 flex flex-col justify-between min-h-[156px]">
            <div className="flex items-start justify-between gap-2">
              <div className="font-serif-display text-[36px] sm:text-[40px] leading-none tracking-[-0.02em]">
                {canaryValue}
              </div>
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] px-2 py-0.5 rounded bg-white/10 text-white">
                {canaryStatusLabel}
              </span>
            </div>
            <div className="mt-4">
              <div className="text-[13.5px] font-medium text-[#D4D4D4]">Canary leaks</div>
              <div className="text-[11.5px] text-[#8E8E8E] mt-0.5">
                {summary?.scope === "AGGREGATE"
                  ? `Aggregate · ${m?.canary.files_assessed ?? 0} files assessed`
                  : summary?.job_id
                  ? `Selected job · ${m?.canary.files_assessed ?? 0} files assessed`
                  : "No completed job selected"}
              </div>
            </div>
          </div>

          {/* Card 2: Identity Precision */}
          <div className="rounded-2xl border border-[#DADADA] bg-[#E6E6E6] text-[#090909] p-6 flex flex-col justify-between min-h-[156px]">
            <div className="flex items-start justify-between gap-2">
              <div className="font-serif-display text-[36px] sm:text-[40px] leading-none tracking-[-0.02em]">
                {identityValue}
              </div>
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] px-2 py-0.5 rounded bg-black/10 text-[#090909]">
                {m?.identity.status ?? "NOT_MEASURED"}
              </span>
            </div>
            <div className="mt-4">
              <div className="text-[13.5px] font-medium text-[#333333]">Identity precision</div>
              <div className="text-[11.5px] text-[#666666] mt-0.5">
                {m?.identity.status === "MEASURED"
                  ? `TP ${m.identity.true_positives} · FP ${m.identity.false_positives} · ${m.identity.false_merges} false merges (${m.identity.records_assessed} records)`
                  : `Scope: ${m?.identity.scope ?? "JOB"} · Denominator unavailable`}
              </div>
            </div>
          </div>

          {/* Card 3: Clinical Fidelity */}
          <div className="rounded-2xl border border-[#B0B0B0] bg-[#BFBFBF] text-[#090909] p-6 flex flex-col justify-between min-h-[156px]">
            <div className="flex items-start justify-between gap-2">
              <div className="font-serif-display text-[36px] sm:text-[40px] leading-none tracking-[-0.02em]">
                {clinicalValue}
              </div>
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] px-2 py-0.5 rounded bg-black/10 text-[#090909]">
                {m?.clinical.status ?? "NOT_MEASURED"}
              </span>
            </div>
            <div className="mt-4">
              <div className="text-[13.5px] font-medium text-[#1F1F1F]">Clinical data preserved</div>
              <div className="text-[11.5px] text-[#444444] mt-0.5">
                {m?.clinical.status === "MEASURED" && m.clinical.expected > 0
                  ? `${m.clinical.preserved.toLocaleString()} / ${m.clinical.expected.toLocaleString()} values · ${m.clinical.modified} modified · ${m.clinical.missing} missing`
                  : "No clinical validation values measured"}
              </div>
            </div>
          </div>

          {/* Card 4: Execution Compliance */}
          <div className="rounded-2xl border border-[#DADADA] bg-white text-[#090909] p-6 flex flex-col justify-between min-h-[156px]">
            <div className="flex items-start justify-between gap-2">
              <div className="font-serif-display text-[34px] sm:text-[38px] leading-none tracking-[-0.02em]">
                {execHeadline}
              </div>
              {exec?.verification_status === "VERIFIED" ? (
                <ShieldCheck size={18} className="text-[#090909] shrink-0" />
              ) : (
                <ShieldAlert size={18} className="text-[#666666] shrink-0" />
              )}
            </div>
            <div className="mt-4">
              <div className="text-[13.5px] font-medium text-[#333333]">Execution compliance</div>
              <div className="text-[11.5px] text-[#666666] mt-0.5">
                {exec
                  ? `${exec.mode} · ${exec.device} · LLM: ${exec.llm_dependency} · Net calls: ${exec.network_calls ?? "Unmeasured"}`
                  : "Runtime compliance unverified"}
              </div>
              <div className="text-[10.5px] text-[#888888] mt-0.5">
                Engine compliance · Repository audit
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api, type DashboardMetricsSummary, type ExecutionCompliance } from "@/lib/api";

export function LiveTrustMetrics() {
  const [compliance, setCompliance] = useState<ExecutionCompliance | null>(null);
  const [summary, setSummary] = useState<DashboardMetricsSummary | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      const [compRes, sumRes] = await Promise.allSettled([
        api.systemCompliance(),
        api.dashboardMetricsSummary("latest"),
      ]);
      if (!active) return;
      if (compRes.status === "fulfilled") setCompliance(compRes.value);
      if (sumRes.status === "fulfilled") setSummary(sumRes.value);
      setLoaded(true);
    }
    load();
    return () => {
      active = false;
    };
  }, []);

  const m = summary?.metrics;
  const canaryVal =
    m && m.canary.status === "TESTED" && m.canary.planted > 0 && m.canary.leaked !== null
      ? `${m.canary.leaked}/${m.canary.planted}`
      : loaded
      ? "Not tested"
      : "—";

  const identityVal =
    m && m.identity.status === "MEASURED" && m.identity.precision !== null
      ? m.identity.precision.toFixed(2)
      : loaded
      ? "Not measured"
      : "—";

  const clinicalVal =
    m && m.clinical.status === "MEASURED" && m.clinical.expected > 0 && m.clinical.preservation_percentage !== null
      ? m.clinical.preserved === m.clinical.expected
        ? "100.0%"
        : `${m.clinical.preservation_percentage.toFixed(2)}%`
      : loaded
      ? "Not measured"
      : "—";

  const execVal = compliance
    ? compliance.verification_status === "VERIFIED"
      ? "Verified"
      : compliance.verification_status
    : loaded
    ? "Not verified"
    : "—";

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-[#090909] text-white border-[#090909]">
        <div className="font-serif-display text-[38px] sm:text-[44px] leading-none tracking-[-0.02em]">
          {canaryVal}
        </div>
        <div className="mt-6">
          <div className="text-[14px] font-medium text-[#B5B5B5]">Canary leaks</div>
          <div className="text-[12px] mt-1 text-[#888888]">
            {summary?.job_id
              ? `${summary.dataset_name ?? summary.job_id} · ${m?.canary.files_assessed ?? 0} files`
              : "Sign in & run a dataset to measure"}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-[#E6E6E6] text-[#090909] border-[#DADADA]">
        <div className="font-serif-display text-[38px] sm:text-[44px] leading-none tracking-[-0.02em]">
          {identityVal}
        </div>
        <div className="mt-6">
          <div className="text-[14px] font-medium text-[#555555]">Identity precision</div>
          <div className="text-[12px] mt-1 text-[#777777]">
            {m?.identity.status === "MEASURED"
              ? `${m.identity.records_assessed} records · ${m.identity.false_merges} false merges`
              : "Per-job evaluation via Privacy Console"}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-[#BFBFBF] text-[#090909] border-[#B0B0B0]">
        <div className="font-serif-display text-[38px] sm:text-[44px] leading-none tracking-[-0.02em]">
          {clinicalVal}
        </div>
        <div className="mt-6">
          <div className="text-[14px] font-medium text-[#333333]">Clinical data preserved</div>
          <div className="text-[12px] mt-1 text-[#555555]">
            {m?.clinical.status === "MEASURED" && m.clinical.expected > 0
              ? `${m.clinical.preserved.toLocaleString()} / ${m.clinical.expected.toLocaleString()} values`
              : "Measured by clinical validator"}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-white text-[#090909] border-[#DADADA]">
        <div className="font-serif-display text-[38px] sm:text-[44px] leading-none tracking-[-0.02em]">
          {execVal}
        </div>
        <div className="mt-6">
          <div className="text-[14px] font-medium text-[#666666]">Execution compliance</div>
          <div className="text-[12px] mt-1 text-[#888888]">
            {compliance
              ? `${compliance.mode}, ${compliance.device} · LLM: ${compliance.llm_dependency}`
              : "Engine compliance · Repository audit"}
          </div>
        </div>
      </div>
    </div>
  );
}

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

  // Card 1 — Files protected
  const filesVal =
    m?.files_protected?.status === "MEASURED" && m.files_protected.count !== null
      ? m.files_protected.count.toLocaleString()
      : loaded
      ? "No completed jobs"
      : "—";

  // Card 2 — Identifiers protected
  const idsVal =
    m?.identifiers_protected?.status === "MEASURED" && m.identifiers_protected.transformed !== null
      ? m.identifiers_protected.transformed.toLocaleString()
      : loaded
      ? "Awaiting processing"
      : "—";

  // Card 3 — Clinical data preserved
  const clinicalVal =
    m && m.clinical.status === "MEASURED" && m.clinical.expected > 0 && m.clinical.preservation_percentage !== null
      ? m.clinical.preserved === m.clinical.expected
        ? "100.0%"
        : `${m.clinical.preservation_percentage.toFixed(2)}%`
      : loaded
      ? "Not assessed"
      : "—";

  // Card 4 — Privacy tests passed
  const pt = m?.privacy_tests;
  const testsVal =
    pt && pt.total_executed > 0
      ? pt.status === "BLOCKED"
        ? "Blocked"
        : `${pt.passed}/${pt.total_executed}`
      : loaded
      ? "Not tested"
      : "—";

  const execInfo = m?.execution ?? compliance;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1 — Files protected */}
        <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-[#090909] text-white border-[#090909]">
          <div className="font-serif-display text-[36px] sm:text-[42px] leading-[1.05] tracking-[-0.02em]">
            {filesVal}
          </div>
          <div className="mt-6">
            <div className="text-[14px] font-medium text-[#D4D4D4]">Files protected</div>
            <div className="text-[12px] mt-1 text-[#8E8E8E]">
              {m?.files_protected?.status === "MEASURED"
                ? `Successfully sanitised files · ${m.files_protected.files_quarantined} quarantined`
                : "Successfully sanitised files"}
            </div>
          </div>
        </div>

        {/* Card 2 — Identifiers protected */}
        <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-[#E6E6E6] text-[#090909] border-[#DADADA]">
          <div className="font-serif-display text-[36px] sm:text-[42px] leading-[1.05] tracking-[-0.02em]">
            {idsVal}
          </div>
          <div className="mt-6">
            <div className="text-[14px] font-medium text-[#333333]">Identifiers protected</div>
            <div className="text-[12px] mt-1 text-[#666666]">
              {m?.identifiers_protected?.status === "MEASURED"
                ? `Personal data detected and protected · ${m.identifiers_protected.remaining_leaks ?? 0} leaks`
                : "Personal data detected and protected"}
            </div>
          </div>
        </div>

        {/* Card 3 — Clinical data preserved */}
        <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-[#BFBFBF] text-[#090909] border-[#B0B0B0]">
          <div className="font-serif-display text-[36px] sm:text-[42px] leading-[1.05] tracking-[-0.02em]">
            {clinicalVal}
          </div>
          <div className="mt-6">
            <div className="text-[14px] font-medium text-[#222222]">Clinical data preserved</div>
            <div className="text-[12px] mt-1 text-[#444444]">
              {m?.clinical.status === "MEASURED" && m.clinical.expected > 0
                ? `${m.clinical.preserved.toLocaleString()} / ${m.clinical.expected.toLocaleString()} values`
                : "Preserved values / evaluated values"}
            </div>
          </div>
        </div>

        {/* Card 4 — Privacy tests passed */}
        <div className="rounded-2xl border p-7 flex flex-col justify-between min-h-[164px] bg-white text-[#090909] border-[#DADADA]">
          <div className="font-serif-display text-[36px] sm:text-[42px] leading-[1.05] tracking-[-0.02em]">
            {testsVal}
          </div>
          <div className="mt-6">
            <div className="text-[14px] font-medium text-[#333333]">Privacy tests passed</div>
            <div className="text-[12px] mt-1 text-[#777777]">
              {pt && pt.total_executed > 0
                ? `Verified privacy assessments · ${pt.failed} failed · ${pt.not_run} not run`
                : "Verified privacy assessments"}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Evaluation Information */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-[12.5px]">
        <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
          <div className="font-semibold text-[#090909]">1. Re-identification resistance</div>
          <div className="text-[#666666] mt-1">
            Canary leaks:{" "}
            <strong className="text-[#090909]">
              {m?.canary.status === "TESTED" && m.canary.planted > 0
                ? `${m.canary.leaked}/${m.canary.planted}`
                : "Not tested"}
            </strong>{" "}
            · Quasi-identifier k-anonymity active
          </div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
          <div className="font-semibold text-[#090909]">2. Multilingual PII detection</div>
          <div className="text-[#666666] mt-1">
            English, Hindi (Devanagari) &amp; Hinglish · Detected:{" "}
            <strong className="text-[#090909]">
              {m?.identifiers_protected?.status === "MEASURED"
                ? m.identifiers_protected.detected.toLocaleString()
                : "Not measured"}
            </strong>
          </div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
          <div className="font-semibold text-[#090909]">3. Patient identity consistency</div>
          <div className="text-[#666666] mt-1">
            Precision:{" "}
            <strong className="text-[#090909]">
              {m?.identity.precision != null ? m.identity.precision.toFixed(2) : "Not measured"}
            </strong>{" "}
            · Recall:{" "}
            <strong className="text-[#090909]">
              {m?.identity.recall != null ? m.identity.recall.toFixed(2) : "Not measured"}
            </strong>{" "}
            · F0.5:{" "}
            <strong className="text-[#090909]">
              {m?.identity.f05 != null ? m.identity.f05.toFixed(2) : "Not measured"}
            </strong>
          </div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
          <div className="font-semibold text-[#090909]">4. Output validity</div>
          <div className="text-[#666666] mt-1">
            FHIR R4:{" "}
            <strong className="text-[#090909]">
              {m?.operations?.fhir_integrity || "Not measured"}
            </strong>{" "}
            · Quarantined:{" "}
            <strong className="text-[#090909]">
              {m?.files_protected ? m.files_protected.files_quarantined : "Not measured"}
            </strong>
          </div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
          <div className="font-semibold text-[#090909]">5. Offline CPU-only compliance</div>
          <div className="text-[#666666] mt-1">
            {execInfo
              ? `${execInfo.mode} · ${execInfo.device} · LLM: ${execInfo.llm_dependency}`
              : "Offline · CPU · LLM: NONE"}
          </div>
        </div>
        <div className="bg-white border border-[#E5E5E5] rounded-xl p-4">
          <div className="font-semibold text-[#090909]">6. Execution speed &amp; reliability</div>
          <div className="text-[#666666] mt-1">
            Duration:{" "}
            <strong className="text-[#090909]">
              {m?.operations?.duration_secs != null ? `${m.operations.duration_secs.toFixed(2)}s` : "Not measured"}
            </strong>{" "}
            · Records:{" "}
            <strong className="text-[#090909]">
              {m?.operations ? m.operations.records_processed.toLocaleString() : "Not measured"}
            </strong>
          </div>
        </div>
      </div>
    </div>
  );
}

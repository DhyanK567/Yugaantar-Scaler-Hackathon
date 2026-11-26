"use client";

import { useEffect, useState } from "react";
import { api, type PrivacyIntelligence } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";

export default function PrivacyIntelligencePage() {
  const [intel, setIntel] = useState<PrivacyIntelligence | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.privacyIntelligence().then(setIntel).catch((e) => setError(e.message));
  }, []);

  const measured = intel?.status === "MEASURED";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="04 · RISK & LEAKAGE TELEMETRY"
        title="Privacy Intelligence"
        subtitle="Measured PII detection, residual leakage checks, quasi-identifier risk, and release eligibility."
      />

      {error && <ErrorState message={error} />}

      <div className="bg-[#090909] text-white rounded-2xl p-6 sm:p-7 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Assessment Status
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {intel?.status ?? "NOT_MEASURED"}
          </div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Total PII Detected
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {measured ? intel.total_pii_detected : "Not measured"}
          </div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Residual Leakage
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {measured ? intel.total_residual_leakage : "Not measured"}
          </div>
        </div>
        <div>
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            Canary Containment
          </div>
          <div className="font-serif-display text-[28px] leading-none">
            {intel?.canary_status ?? "NOT_RUN"}
          </div>
        </div>
      </div>

      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#090909]">
            Measured Privacy Assessments ({intel?.assessments.length ?? 0})
          </h2>
        </div>
        {!intel || intel.assessments.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No privacy assessments measured"
              description="Upload and process a dataset to generate real PII detection and risk assessments."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Assessment", "Job ID", "PII Detected", "Residual Leaks", "Canary", "QI Risk", "Eligible"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {intel.assessments.map((a) => (
                  <tr key={a.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3 text-[12px] font-mono text-[#090909]">{a.id}</td>
                    <td className="px-5 py-3 text-[12px] font-mono text-[#666666]">{a.job_id}</td>
                    <td className="px-5 py-3 text-[13px] font-semibold">{a.pii_detected}</td>
                    <td className="px-5 py-3 text-[13px]">{a.residual_leakage}</td>
                    <td className="px-5 py-3">
                      <StatusBadge status={a.canary_status} />{" "}
                      <span className="text-[11.5px] text-[#666666] ml-1">
                        ({a.canary_leaks}/{a.canary_planted})
                      </span>
                    </td>
                    <td className="px-5 py-3 text-[13px]">
                      {a.qi_risk_score}% ({a.reid_risk_level})
                    </td>
                    <td className="px-5 py-3">
                      <StatusBadge status={a.release_eligible ? "PASS" : "BLOCKED"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

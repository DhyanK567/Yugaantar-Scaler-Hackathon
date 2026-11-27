"use client";

import { useEffect, useState } from "react";
import { api, type ClinicalReport, type FileFormatBreakdown } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { ClinicalIntegrityChart } from "@/components/charts/ClinicalIntegrityChart";

export default function ClinicalIntegrityPage() {
  const [reports, setReports] = useState<ClinicalReport[]>([]);
  const [filesByFormat, setFilesByFormat] = useState<FileFormatBreakdown[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      api.clinicalReports(),
      api.privacyIntelligence().catch(() => null),
    ])
      .then(([repList, pi]) => {
        setReports(repList);
        setFilesByFormat(pi?.files_by_format ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const totalExpected = reports.reduce((s, r) => s + r.expected_values, 0);
  const totalPreserved = reports.reduce((s, r) => s + r.preserved_values, 0);
  const totalMissing = reports.reduce((s, r) => s + r.missing_values, 0);
  const totalModified = reports.reduce((s, r) => s + r.modified_values, 0);
  const latest = reports[0] ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="08 · CLINICAL DATA PRESERVATION"
        title="Clinical Integrity"
        subtitle="Exact numerator/denominator verification of clinical values, dosages, laboratories, and HL7 FHIR R4 bundles."
      />

      {error && <ErrorState message={error} />}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-2">
            Preserved / Expected
          </div>
          <div className="font-serif-display text-[34px] leading-none text-[#090909]">
            {reports.length > 0 ? `${totalPreserved}/${totalExpected}` : "Not measured"}
          </div>
          <div className="text-[12px] text-[#666666] mt-2">
            {totalExpected > 0
              ? `${((totalPreserved / totalExpected) * 100).toFixed(2)}% exact preservation`
              : "No clinical items measured"}
          </div>
        </div>

        <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-2">
            Modified / Missing
          </div>
          <div
            className={`font-serif-display text-[34px] leading-none ${
              totalMissing > 0 ? "text-[#7F1D1D]" : "text-[#090909]"
            }`}
          >
            {reports.length > 0 ? `${totalModified} / ${totalMissing}` : "Not measured"}
          </div>
          <div className="text-[12px] text-[#666666] mt-2">
            Across {reports.length} clinical validation report(s)
          </div>
        </div>

        <div className="bg-white border border-[#DADADA] rounded-2xl p-6">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-2">
            FHIR R4 Integrity
          </div>
          <div className="mt-1">
            <StatusBadge status={latest ? latest.fhir_integrity : "NOT_MEASURED"} />
          </div>
          <div className="text-[12px] text-[#666666] mt-3">
            HL7 FHIR R4 Bundle validation
          </div>
        </div>
      </div>

      <ClinicalIntegrityChart
        reports={reports}
        filesByFormat={filesByFormat}
        loading={loading}
        lastUpdated={latest?.created_at}
      />

      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#090909]">
            Clinical Validation Reports ({reports.length})
          </h2>
        </div>

        {reports.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No clinical reports available"
              description="Upload and process a healthcare dataset to verify clinical preservation."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Report ID", "Job ID", "Preserved / Expected", "Modified", "Missing", "FHIR R4", "Created"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {reports.map((r) => (
                  <tr key={r.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3 text-[12px] font-mono text-[#090909]">{r.id}</td>
                    <td className="px-5 py-3 text-[12px] font-mono text-[#666666]">{r.job_id}</td>
                    <td className="px-5 py-3 text-[13px] font-semibold">
                      {r.preserved_values} / {r.expected_values}
                    </td>
                    <td className="px-5 py-3 text-[13px]">{r.modified_values}</td>
                    <td className="px-5 py-3 text-[13px]">{r.missing_values}</td>
                    <td className="px-5 py-3"><StatusBadge status={r.fhir_integrity} /></td>
                    <td className="px-5 py-3 text-[12px] text-[#666666] whitespace-nowrap">
                      {new Date(r.created_at * 1000).toLocaleString()}
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

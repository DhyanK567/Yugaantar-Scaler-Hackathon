"use client";

import React, { useState } from "react";
import type { ClinicalReport, FileFormatBreakdown } from "@/lib/api";
import { ChartCard } from "./ChartCard";

export interface ClinicalIntegrityChartProps {
  reports: ClinicalReport[];
  filesByFormat?: FileFormatBreakdown[];
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

export function ClinicalIntegrityChart({
  reports,
  filesByFormat = [],
  loading = false,
  error = "",
  lastUpdated,
}: ClinicalIntegrityChartProps) {
  const [hoveredSegment, setHoveredSegment] = useState<string | null>(null);

  const totalExpected = reports.reduce((s, r) => s + r.expected_values, 0);
  const totalPreserved = reports.reduce((s, r) => s + r.preserved_values, 0);
  const totalModified = reports.reduce((s, r) => s + r.modified_values, 0);
  const totalMissing = reports.reduce((s, r) => s + r.missing_values, 0);

  const fidelityPct =
    totalExpected > 0 ? (totalPreserved / totalExpected) * 100 : null;

  const segments = [
    { key: "preserved", label: "Preserved", value: totalPreserved, color: "#166534" },
    { key: "modified", label: "Modified", value: totalModified, color: "#92400E" },
    { key: "missing", label: "Missing / Lost", value: totalMissing, color: "#991B1B" },
  ].filter((s) => s.value > 0);

  const totalSeg = segments.reduce((s, x) => s + x.value, 0);
  const radius = 62;
  const strokeWidth = 20;
  const cx = 86;
  const cy = 86;
  const circumference = 2 * Math.PI * radius;

  let cumulative = 0;
  const donutSegs = segments.map((seg) => {
    const pct = totalSeg > 0 ? seg.value / totalSeg : 0;
    const dash = pct * circumference;
    const offset = -cumulative * circumference;
    cumulative += pct;
    return { ...seg, pct, dash, offset };
  });

  const maxFormatFiles = Math.max(1, ...filesByFormat.map((f) => f.total));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* Clinical Preservation Breakdown */}
      <ChartCard
        title="Clinical Value Preservation"
        subtitle="Exact numerator/denominator fidelity across medications, dosages, labs, and vitals."
        unit="Values (%)"
        source="/api/clinical/reports"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={reports.length === 0 || totalExpected === 0}
        emptyTitle="Clinical preservation not measured"
        emptyDescription="Process a dataset containing clinical fields to measure exact preservation vs. drift."
      >
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <svg
            viewBox="0 0 172 172"
            className="w-[168px] h-[168px] shrink-0"
            role="img"
            aria-label="Clinical Preservation Donut Chart"
          >
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke="#F0F0EE"
              strokeWidth={strokeWidth}
            />
            {donutSegs.map((seg) => (
              <circle
                key={seg.key}
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={hoveredSegment === seg.key ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={`${seg.dash} ${circumference}`}
                strokeDashoffset={seg.offset}
                transform={`rotate(-90 ${cx} ${cy})`}
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredSegment(seg.key)}
                onMouseLeave={() => setHoveredSegment(null)}
              />
            ))}
            <text
              x={cx}
              y={cy - 3}
              textAnchor="middle"
              className="fill-[#090909] font-serif-display text-[22px]"
            >
              {fidelityPct !== null ? `${fidelityPct.toFixed(1)}%` : "—"}
            </text>
            <text
              x={cx}
              y={cy + 14}
              textAnchor="middle"
              className="fill-[#666666] text-[10px] uppercase tracking-wider"
            >
              Preserved
            </text>
          </svg>

          <div className="flex-1 w-full space-y-2.5">
            {[
              { key: "preserved", label: "Clinical Values Preserved", val: totalPreserved, color: "#166534" },
              { key: "modified", label: "Modified Values", val: totalModified, color: "#92400E" },
              { key: "missing", label: "Missing / Lost Values", val: totalMissing, color: "#991B1B" },
            ].map((item) => (
              <div
                key={item.key}
                onMouseEnter={() => setHoveredSegment(item.key)}
                onMouseLeave={() => setHoveredSegment(null)}
                className="flex items-center justify-between px-3 py-2 rounded-lg border border-[#E5E5E5] bg-[#F9F9F8]"
              >
                <span className="flex items-center gap-2 text-[12.5px] font-medium text-[#090909]">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: item.color }} />
                  {item.label}
                </span>
                <span className="font-mono text-[12.5px] font-semibold text-[#090909]">
                  {item.val} / {totalExpected}
                </span>
              </div>
            ))}
          </div>
        </div>
      </ChartCard>

      {/* Document-wise Integrity */}
      <ChartCard
        title="Document-wise Integrity"
        subtitle="Sanitised vs. quarantined files grouped by actual clinical document format."
        unit="Files"
        source="/api/privacy-intelligence (report.json)"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={filesByFormat.length === 0}
        emptyTitle="No document format breakdown available"
        emptyDescription="Process a dataset job to inspect sanitised vs. quarantined counts across CSV, JSON, FHIR, and Text documents."
        headerRight={
          filesByFormat.length > 0 ? (
            <div className="flex items-center gap-3 text-[11px] text-[#666666]">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-[#090909]" />
                Sanitised
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-[#92400E]" />
                Quarantined
              </span>
            </div>
          ) : null
        }
      >
        <div className="space-y-3">
          {filesByFormat.map((fmt) => {
            const sanW = Math.round((fmt.sanitized / maxFormatFiles) * 100);
            const quarW = Math.round((fmt.quarantined / maxFormatFiles) * 100);
            return (
              <div key={fmt.format} className="space-y-1.5">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="font-semibold text-[#090909]">{fmt.format}</span>
                  <span className="font-mono text-[11.5px] text-[#666666]">
                    {fmt.sanitized} sanitised · {fmt.quarantined} quarantined · {fmt.records} records
                  </span>
                </div>
                <div className="h-3 w-full bg-[#F4F4F2] rounded-full overflow-hidden flex">
                  {fmt.sanitized > 0 && (
                    <div
                      className="h-full bg-[#090909]"
                      style={{ width: `${sanW}%` }}
                    />
                  )}
                  {fmt.quarantined > 0 && (
                    <div
                      className="h-full bg-[#92400E]"
                      style={{ width: `${quarW}%` }}
                    />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </ChartCard>
    </div>
  );
}

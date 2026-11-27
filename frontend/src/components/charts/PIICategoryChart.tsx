"use client";

import React, { useState } from "react";
import { ChartCard } from "./ChartCard";

export interface PIICategoryChartProps {
  fieldTierCounts?: Record<string, number>;
  totalDetected?: number;
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

const PALETTE = ["#090909", "#444444", "#737373", "#A3A3A3", "#166534", "#92400E"];

const TIER_LABELS: Record<string, string> = {
  DIRECT_IDENTIFIER: "Direct Identifiers (Names, IDs, Phones)",
  QUASI_IDENTIFIER: "Quasi-Identifiers (Age, Gender, Geo)",
  CLINICAL: "Clinical / Protected Health Terms",
  METADATA: "Record & Provenance Metadata",
  OTHER: "Other Classified Fields",
};

function formatCategoryLabel(raw: string): string {
  if (TIER_LABELS[raw]) return TIER_LABELS[raw];
  return raw
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function PIICategoryChart({
  fieldTierCounts = {},
  totalDetected = 0,
  loading = false,
  error = "",
  lastUpdated,
}: PIICategoryChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const entries = Object.entries(fieldTierCounts)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1]);

  const total = entries.reduce((s, [, v]) => s + v, 0);

  const radius = 64;
  const strokeWidth = 22;
  const cx = 90;
  const cy = 90;
  const circumference = 2 * Math.PI * radius;

  let cumulative = 0;
  const segments = entries.map(([key, value], idx) => {
    const pct = total > 0 ? value / total : 0;
    const dash = pct * circumference;
    const offset = -cumulative * circumference;
    cumulative += pct;
    return {
      key,
      label: formatCategoryLabel(key),
      value,
      pct,
      dash,
      offset,
      color: PALETTE[idx % PALETTE.length],
    };
  });

  const hovered = hoveredIdx !== null ? segments[hoveredIdx] : null;

  return (
    <ChartCard
      title="Field & Identifier Classification"
      subtitle="Distribution of classified field tiers and protected identifiers from the engine report."
      unit="Fields"
      source="/api/privacy-intelligence (report.json)"
      lastUpdated={lastUpdated}
      loading={loading}
      error={error}
      empty={segments.length === 0}
      emptyTitle={
        totalDetected > 0
          ? `${totalDetected} identifiers protected (category breakdown unavailable)`
          : "No field classification data"
      }
      emptyDescription={
        totalDetected > 0
          ? "This run recorded aggregate identifier counts without per-category breakdown in report.json."
          : "Run a dataset processing job to inspect field tier and identifier classification."
      }
    >
      <div className="flex flex-col sm:flex-row items-center gap-6">
        <div className="relative shrink-0">
          <svg
            viewBox="0 0 180 180"
            className="w-[176px] h-[176px]"
            role="img"
            aria-label="Field and Identifier Classification Donut Chart"
          >
            <circle
              cx={cx}
              cy={cy}
              r={radius}
              fill="none"
              stroke="#F0F0EE"
              strokeWidth={strokeWidth}
            />
            {segments.map((seg, i) => (
              <circle
                key={seg.key}
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke={seg.color}
                strokeWidth={hoveredIdx === i ? strokeWidth + 4 : strokeWidth}
                strokeDasharray={`${seg.dash} ${circumference}`}
                strokeDashoffset={seg.offset}
                transform={`rotate(-90 ${cx} ${cy})`}
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
              />
            ))}
            <text
              x={cx}
              y={cy - 4}
              textAnchor="middle"
              className="fill-[#090909] font-serif-display text-[22px]"
            >
              {hovered ? hovered.value : total}
            </text>
            <text
              x={cx}
              y={cy + 14}
              textAnchor="middle"
              className="fill-[#666666] text-[10px] uppercase tracking-wider"
            >
              {hovered ? `${(hovered.pct * 100).toFixed(1)}%` : "Total"}
            </text>
          </svg>
        </div>

        <div className="flex-1 w-full space-y-2">
          {segments.map((seg, i) => (
            <div
              key={seg.key}
              onMouseEnter={() => setHoveredIdx(i)}
              onMouseLeave={() => setHoveredIdx(null)}
              className={`flex items-center justify-between gap-3 px-3 py-2 rounded-lg border transition-colors cursor-pointer ${
                hoveredIdx === i
                  ? "bg-[#F4F4F2] border-[#090909]"
                  : "bg-white border-[#E5E5E5]"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: seg.color }}
                />
                <span className="text-[12.5px] font-medium text-[#090909] truncate">
                  {seg.label}
                </span>
              </div>
              <div className="text-[12px] text-[#444444] shrink-0 font-mono">
                {seg.value} ({(seg.pct * 100).toFixed(1)}%)
              </div>
            </div>
          ))}
          {totalDetected > 0 && (
            <div className="text-[11.5px] text-[#666666] pt-1">
              Total direct identifiers detected &amp; protected in run:{" "}
              <strong className="text-[#090909]">{totalDetected}</strong>
            </div>
          )}
        </div>
      </div>
    </ChartCard>
  );
}

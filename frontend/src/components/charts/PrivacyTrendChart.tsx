"use client";

import React, { useState } from "react";
import type { JobRecord, PrivacyAssessment } from "@/lib/api";
import { ChartCard, fmtShortDate, fmtShortTime } from "./ChartCard";

export interface PrivacyTrendChartProps {
  jobs: JobRecord[];
  assessments?: PrivacyAssessment[];
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

interface TrendPoint {
  jobId: string;
  label: string;
  timestamp: number;
  detected: number;
  sanitised: number;
  residual: number | null;
}

export function PrivacyTrendChart({
  jobs,
  assessments = [],
  loading = false,
  error = "",
  lastUpdated,
}: PrivacyTrendChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const assessmentByJob = new Map<string, PrivacyAssessment>();
  for (const a of assessments) {
    if (a.job_id && !assessmentByJob.has(a.job_id)) {
      assessmentByJob.set(a.job_id, a);
    }
  }

  // Chronological order (oldest -> newest) across completed/assessed jobs
  const completedJobs = [...jobs]
    .filter((j) =>
      ["COMPLETED", "COMPLETED_WITH_WARNINGS", "BLOCKED", "QUARANTINED"].includes(
        (j.status || "").toUpperCase()
      )
    )
    .sort((a, b) => (a.completed_at || a.created_at) - (b.completed_at || b.created_at))
    .slice(-10);

  const points: TrendPoint[] = completedJobs.map((j) => {
    const a = assessmentByJob.get(j.id);
    const detected = a ? a.pii_detected : (j.identifiers_detected ?? 0);
    const residual = a ? a.residual_leakage : null;
    const sanitised =
      residual !== null ? Math.max(0, detected - residual) : detected;
    const ts = j.completed_at || j.created_at;
    return {
      jobId: j.id,
      label: j.dataset_name || j.input_name || j.id.slice(0, 10),
      timestamp: ts,
      detected,
      sanitised,
      residual,
    };
  });

  const maxVal = Math.max(1, ...points.map((p) => p.detected));
  const width = 560;
  const height = 220;
  const padL = 44;
  const padR = 16;
  const padT = 18;
  const padB = 42;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const stepX = points.length > 0 ? plotW / points.length : plotW;
  const barW = Math.min(28, Math.max(10, stepX * 0.36));

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(maxVal * t));

  const hovered = hoveredIdx !== null ? points[hoveredIdx] : null;

  return (
    <ChartCard
      title="Privacy Protection Trend"
      subtitle="PII entities detected, sanitised, and remaining exposure across completed runs."
      unit="Entities"
      source="/api/dashboard/overview + /api/privacy-intelligence"
      lastUpdated={lastUpdated}
      loading={loading}
      error={error}
      empty={points.length === 0}
      emptyTitle="No completed protection runs yet"
      emptyDescription="Run a dataset through the privacy engine to plot PII detection and sanitisation trends over time."
      headerRight={
        points.length > 0 ? (
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-[#666666]">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#090909]" />
              Detected
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#166534]" />
              Sanitised
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#991B1B]" />
              Residual Exposure
            </span>
          </div>
        ) : null
      }
    >
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible"
          role="img"
          aria-label="Privacy Protection Trend Chart"
        >
          {/* Horizontal grid lines */}
          {yTicks.map((tick, idx) => {
            const y = padT + plotH - (tick / maxVal) * plotH;
            return (
              <g key={idx}>
                <line
                  x1={padL}
                  y1={y}
                  x2={width - padR}
                  y2={y}
                  stroke="#E5E5E5"
                  strokeDasharray={idx === 0 ? undefined : "3 3"}
                />
                <text
                  x={padL - 8}
                  y={y + 3.5}
                  textAnchor="end"
                  className="fill-[#888888] text-[10px]"
                >
                  {tick}
                </text>
              </g>
            );
          })}

          {/* Bars per job */}
          {points.map((p, i) => {
            const cx = padL + i * stepX + stepX / 2;
            const detH = (p.detected / maxVal) * plotH;
            const sanH = (p.sanitised / maxVal) * plotH;
            const resH = p.residual !== null ? (p.residual / maxVal) * plotH : 0;
            const isHovered = hoveredIdx === i;

            return (
              <g
                key={p.jobId}
                onMouseEnter={() => setHoveredIdx(i)}
                onMouseLeave={() => setHoveredIdx(null)}
                className="cursor-pointer"
              >
                {isHovered && (
                  <rect
                    x={cx - stepX / 2 + 2}
                    y={padT}
                    width={stepX - 4}
                    height={plotH}
                    fill="#F4F4F2"
                    rx={4}
                  />
                )}
                {/* Detected bar */}
                <rect
                  x={cx - barW - 1.5}
                  y={padT + plotH - detH}
                  width={barW}
                  height={Math.max(2, detH)}
                  fill="#090909"
                  rx={2}
                  opacity={isHovered ? 1 : 0.88}
                />
                {/* Sanitised bar */}
                <rect
                  x={cx + 1.5}
                  y={padT + plotH - sanH}
                  width={barW}
                  height={Math.max(2, sanH)}
                  fill="#166534"
                  rx={2}
                  opacity={isHovered ? 1 : 0.9}
                />
                {/* Residual marker if > 0 */}
                {p.residual !== null && p.residual > 0 && (
                  <circle
                    cx={cx}
                    cy={padT + plotH - resH}
                    r={4}
                    fill="#991B1B"
                    stroke="#FFFFFF"
                    strokeWidth={1.5}
                  />
                )}
                {/* Time-based X-axis label */}
                <text
                  x={cx}
                  y={padT + plotH + 15}
                  textAnchor="middle"
                  className="fill-[#444444] text-[9.5px] font-medium"
                >
                  {fmtShortTime(p.timestamp)}
                </text>
                <text
                  x={cx}
                  y={padT + plotH + 27}
                  textAnchor="middle"
                  className="fill-[#888888] text-[9px]"
                >
                  {fmtShortDate(p.timestamp)}
                </text>
              </g>
            );
          })}
        </svg>

        {hovered && (
          <div className="mt-2 px-3.5 py-2.5 rounded-xl bg-[#090909] text-white text-[11.5px] flex flex-wrap items-center justify-between gap-3">
            <div>
              <span className="font-semibold">{hovered.label}</span>
              <span className="text-[#AAAAAA] ml-2 font-mono text-[10.5px]">
                {hovered.jobId}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-4">
              <span>Detected: <strong>{hovered.detected}</strong></span>
              <span>Sanitised: <strong>{hovered.sanitised}</strong></span>
              <span>
                Exposure:{" "}
                <strong>
                  {hovered.residual !== null ? hovered.residual : "Not measured"}
                </strong>
              </span>
            </div>
          </div>
        )}
      </div>
    </ChartCard>
  );
}

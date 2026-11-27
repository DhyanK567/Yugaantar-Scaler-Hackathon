"use client";

import React, { useState } from "react";
import type { JobRecord } from "@/lib/api";
import { ChartCard, fmtShortDate, fmtShortTime } from "./ChartCard";

export interface ProcessingPerformanceChartProps {
  jobs: JobRecord[];
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

export function ProcessingPerformanceChart({
  jobs,
  loading = false,
  error = "",
  lastUpdated,
}: ProcessingPerformanceChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const ordered = [...jobs]
    .sort((a, b) => (a.completed_at || a.created_at) - (b.completed_at || b.created_at))
    .slice(-10);

  const maxRecords = Math.max(1, ...ordered.map((j) => j.records_processed ?? 0));
  const maxDuration = Math.max(0.1, ...ordered.map((j) => j.duration_secs ?? 0));

  const width = 560;
  const height = 220;
  const padL = 46;
  const padR = 44;
  const padT = 18;
  const padB = 42;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const stepX = ordered.length > 0 ? plotW / ordered.length : plotW;
  const barW = Math.min(26, Math.max(10, stepX * 0.42));

  const lineCoords = ordered.map((j, i) => {
    const cx = padL + i * stepX + stepX / 2;
    const dur = j.duration_secs ?? 0;
    const cy = padT + plotH - (dur / maxDuration) * plotH;
    return { x: cx, y: cy, dur };
  });

  const linePath =
    lineCoords.length > 1
      ? lineCoords.map((pt, i) => `${i === 0 ? "M" : "L"}${pt.x.toFixed(1)},${pt.y.toFixed(1)}`).join(" ")
      : "";

  const hovered = hoveredIdx !== null ? ordered[hoveredIdx] : null;

  return (
    <ChartCard
      title="Processing Performance"
      subtitle="Records processed, execution duration (s), and file quarantine counts per run."
      unit="Records · Secs"
      source="/api/dashboard/overview"
      lastUpdated={lastUpdated}
      loading={loading}
      error={error}
      empty={ordered.length === 0}
      emptyTitle="No processing runs recorded"
      emptyDescription="Upload and process a synthetic dataset to observe throughput, duration, and quarantine behaviour."
      headerRight={
        ordered.length > 0 ? (
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-[#666666]">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-sm bg-[#444444]" />
              Records
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-[#090909]" />
              Duration (s)
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#92400E]" />
              Quarantined
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
          aria-label="Processing Performance Chart"
        >
          {[0, 0.25, 0.5, 0.75, 1].map((t, idx) => {
            const y = padT + plotH - t * plotH;
            const recTick = Math.round(maxRecords * t);
            const durTick = (maxDuration * t).toFixed(1);
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
                  {recTick}
                </text>
                <text
                  x={width - padR + 8}
                  y={y + 3.5}
                  textAnchor="start"
                  className="fill-[#888888] text-[10px]"
                >
                  {durTick}s
                </text>
              </g>
            );
          })}

          {ordered.map((j, i) => {
            const cx = padL + i * stepX + stepX / 2;
            const recs = j.records_processed ?? 0;
            const recH = (recs / maxRecords) * plotH;
            const ts = j.completed_at || j.created_at;
            const isHovered = hoveredIdx === i;

            return (
              <g
                key={j.id}
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
                <rect
                  x={cx - barW / 2}
                  y={padT + plotH - recH}
                  width={barW}
                  height={Math.max(2, recH)}
                  fill="#444444"
                  rx={2}
                  opacity={isHovered ? 1 : 0.8}
                />
                {(j.files_quarantined ?? 0) > 0 && (
                  <circle
                    cx={cx}
                    cy={padT + 8}
                    r={4}
                    fill="#92400E"
                    stroke="#FFFFFF"
                    strokeWidth={1.2}
                  />
                )}
                <text
                  x={cx}
                  y={padT + plotH + 15}
                  textAnchor="middle"
                  className="fill-[#444444] text-[9.5px] font-medium"
                >
                  {fmtShortTime(ts)}
                </text>
                <text
                  x={cx}
                  y={padT + plotH + 27}
                  textAnchor="middle"
                  className="fill-[#888888] text-[9px]"
                >
                  {fmtShortDate(ts)}
                </text>
              </g>
            );
          })}

          {linePath && (
            <path
              d={linePath}
              fill="none"
              stroke="#090909"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
          {lineCoords.map((pt, i) => (
            <circle
              key={i}
              cx={pt.x}
              cy={pt.y}
              r={hoveredIdx === i ? 4.5 : 3}
              fill="#090909"
              stroke="#FFFFFF"
              strokeWidth={1.5}
            />
          ))}
        </svg>

        {hovered && (
          <div className="mt-2 px-3.5 py-2.5 rounded-xl bg-[#090909] text-white text-[11.5px] flex flex-wrap items-center justify-between gap-3">
            <span className="font-semibold">
              {hovered.dataset_name || hovered.input_name || hovered.id}
            </span>
            <div className="flex flex-wrap items-center gap-4">
              <span>Records: <strong>{hovered.records_processed ?? 0}</strong></span>
              <span>
                Files: <strong>{hovered.files_sanitized ?? 0}/{hovered.files_total ?? 0}</strong> sanitised
                {(hovered.files_quarantined ?? 0) > 0
                  ? ` (${hovered.files_quarantined} quarantined)`
                  : ""}
              </span>
              <span>
                Duration:{" "}
                <strong>
                  {hovered.duration_secs != null ? `${hovered.duration_secs.toFixed(2)}s` : "—"}
                </strong>
              </span>
            </div>
          </div>
        )}
      </div>
    </ChartCard>
  );
}

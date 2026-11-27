"use client";

import React from "react";
import { AlertTriangle, BarChart3 } from "lucide-react";

export interface ChartCardProps {
  title: string;
  subtitle?: string;
  unit?: string;
  source?: string;
  lastUpdated?: number | null;
  loading?: boolean;
  error?: string;
  empty?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  headerRight?: React.ReactNode;
  children?: React.ReactNode;
}

export function fmtChartTimestamp(ts?: number | null): string {
  if (!ts) return "Not recorded";
  return new Date(ts * 1000).toLocaleString();
}

export function fmtShortTime(ts?: number | null): string {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function fmtShortDate(ts?: number | null): string {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export function ChartCard({
  title,
  subtitle,
  unit,
  source,
  lastUpdated,
  loading = false,
  error = "",
  empty = false,
  emptyTitle = "Not measured",
  emptyDescription = "Process a synthetic healthcare dataset to populate this visualization with actual telemetry.",
  headerRight,
  children,
}: ChartCardProps) {
  return (
    <div className="bg-white border border-[#DADADA] rounded-2xl p-5 sm:p-6 flex flex-col justify-between gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#E5E5E5] pb-3.5">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-serif-display text-[20px] leading-tight text-[#090909]">
              {title}
            </h3>
            {unit && (
              <span className="text-[10px] font-semibold uppercase tracking-[0.06em] px-2 py-0.5 rounded bg-[#F4F4F2] border border-[#E5E5E5] text-[#666666]">
                {unit}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[12px] text-[#666666] mt-1">{subtitle}</p>
          )}
        </div>
        {headerRight && <div className="shrink-0">{headerRight}</div>}
      </div>

      {error ? (
        <div className="px-4 py-3 rounded-xl bg-[#FFFBF0] border border-[#E6D5A0] text-[12.5px] text-[#7A5C00] flex items-center gap-2">
          <AlertTriangle size={15} className="shrink-0" />
          <span>{error}</span>
        </div>
      ) : loading ? (
        <div className="h-[220px] rounded-xl bg-[#F4F4F2]/70 animate-pulse flex items-center justify-center text-[12.5px] text-[#888888]">
          Loading telemetry…
        </div>
      ) : empty ? (
        <div className="min-h-[190px] rounded-xl border border-dashed border-[#DADADA] bg-[#F9F9F8] p-6 flex flex-col items-center justify-center text-center gap-2">
          <BarChart3 size={22} className="text-[#888888]" />
          <div className="text-[13.5px] font-semibold text-[#090909]">{emptyTitle}</div>
          <p className="text-[12px] text-[#666666] max-w-md">{emptyDescription}</p>
        </div>
      ) : (
        <div className="w-full">{children}</div>
      )}

      {(source || lastUpdated !== undefined) && (
        <div className="pt-2.5 border-t border-[#F0F0EE] flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#888888]">
          <span>{source ? `Source: ${source}` : ""}</span>
          <span>
            {lastUpdated !== undefined
              ? `Updated: ${fmtChartTimestamp(lastUpdated)}`
              : ""}
          </span>
        </div>
      )}
    </div>
  );
}

"use client";

import React from "react";
import type { AuditEvent, Passport } from "@/lib/api";
import { ChartCard } from "./ChartCard";

export interface AuditActivityChartProps {
  events?: AuditEvent[];
  passports?: Passport[];
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

export function AuditActivityChart({
  events = [],
  passports = [],
  loading = false,
  error = "",
  lastUpdated,
}: AuditActivityChartProps) {
  if (passports.length > 0 || events.length === 0) {
    const signed = passports.filter(
      (p) => p.signature_status && p.signature_status !== "UNSIGNED"
    ).length;
    const unsigned = passports.length - signed;
    const total = passports.length;

    return (
      <ChartCard
        title="Passport & Manifest Verification Status"
        subtitle="Cryptographic signature and dataset integrity distribution across issued Privacy Passports."
        unit="Passports"
        source="/api/passports"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={total === 0}
        emptyTitle="No Privacy Passports issued"
        emptyDescription="Process a dataset to issue hash-verified Privacy Passports."
      >
        <div className="space-y-3">
          {[
            { label: "Verified / Signed Manifests", count: signed, color: "#166534" },
            { label: "Unsigned (Local Hash Only)", count: unsigned, color: "#92400E" },
          ].map((row) => {
            const pct = total > 0 ? Math.round((row.count / total) * 100) : 0;
            return (
              <div key={row.label} className="space-y-1">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="font-medium text-[#090909]">{row.label}</span>
                  <span className="font-mono text-[12px] text-[#666666]">
                    {row.count} / {total} ({pct}%)
                  </span>
                </div>
                <div className="h-2.5 w-full bg-[#F4F4F2] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${pct}%`, backgroundColor: row.color }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </ChartCard>
    );
  }

  // Audit event distribution by action
  const actionCounts = new Map<string, number>();
  for (const ev of events) {
    actionCounts.set(ev.action, (actionCounts.get(ev.action) ?? 0) + 1);
  }
  const topActions = [...actionCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const maxCount = Math.max(1, ...topActions.map(([, c]) => c));

  return (
    <ChartCard
      title="Audit Event Distribution"
      subtitle="Breakdown of recorded governance actions in the current audit window."
      unit="Events"
      source="/api/audit/events"
      lastUpdated={lastUpdated}
      loading={loading}
      error={error}
      empty={topActions.length === 0}
      emptyTitle="No audit events recorded"
      emptyDescription="Dataset uploads, job runs, and verification checks appear here."
    >
      <div className="space-y-2.5">
        {topActions.map(([action, count]) => (
          <div key={action} className="space-y-1">
            <div className="flex items-center justify-between text-[12px]">
              <span className="font-mono font-medium text-[#090909]">{action}</span>
              <span className="font-mono text-[12px] text-[#666666]">{count}</span>
            </div>
            <div className="h-2 w-full bg-[#F4F4F2] rounded-full overflow-hidden">
              <div
                className="h-full bg-[#090909] rounded-full"
                style={{ width: `${Math.round((count / maxCount) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </ChartCard>
  );
}

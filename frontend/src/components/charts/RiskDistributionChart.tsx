"use client";

import React from "react";
import type { PrivacyIntelligence } from "@/lib/api";
import { ChartCard } from "./ChartCard";

export interface RiskDistributionChartProps {
  riskMap?: PrivacyIntelligence["risk_map"];
  beforeAfter?: PrivacyIntelligence["before_after"];
  attackOverview?: PrivacyIntelligence["attack_overview"];
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

const RISK_LEVELS = ["LOW", "MODERATE", "HIGH", "CRITICAL"] as const;

const LEVEL_COLORS: Record<string, string> = {
  LOW: "#166534",
  MODERATE: "#737373",
  HIGH: "#92400E",
  CRITICAL: "#991B1B",
};

export function RiskDistributionChart({
  riskMap,
  beforeAfter,
  attackOverview,
  loading = false,
  error = "",
  lastUpdated,
}: RiskDistributionChartProps) {
  const preCats = beforeAfter?.pre_risk_categories || riskMap?.pre_categories || {};
  const postCats = beforeAfter?.post_risk_categories || riskMap?.post_categories || {
    LOW: riskMap?.low ?? 0,
    MODERATE: riskMap?.moderate ?? 0,
    HIGH: riskMap?.high ?? 0,
    CRITICAL: riskMap?.critical ?? 0,
  };

  const hasRiskData = RISK_LEVELS.some(
    (lvl) => (preCats[lvl] ?? 0) > 0 || (postCats[lvl] ?? 0) > 0
  );

  const maxRiskCount = Math.max(
    1,
    ...RISK_LEVELS.map((lvl) => Math.max(preCats[lvl] ?? 0, postCats[lvl] ?? 0))
  );

  const attackStrategies = attackOverview?.strategies ?? [];
  const hasAttack =
    attackOverview?.status === "MEASURED" && attackStrategies.length > 0;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* Before vs After Risk Severity Distribution */}
      <ChartCard
        title="Privacy Risk Distribution"
        subtitle="Record-level quasi-identifier risk severity before vs. after sanitisation."
        unit="Records"
        source="/api/privacy-intelligence"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={!hasRiskData}
        emptyTitle="No risk distribution measured"
        emptyDescription="Process a dataset job to compare pre-sanitisation vs. post-sanitisation record risk."
        headerRight={
          hasRiskData ? (
            <div className="flex items-center gap-3 text-[11px] text-[#666666]">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-[#A3A3A3]" />
                Before
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm bg-[#090909]" />
                After
              </span>
            </div>
          ) : null
        }
      >
        <div className="space-y-3.5">
          {RISK_LEVELS.map((lvl) => {
            const pre = preCats[lvl] ?? 0;
            const post = postCats[lvl] ?? 0;
            const preW = Math.round((pre / maxRiskCount) * 100);
            const postW = Math.round((post / maxRiskCount) * 100);
            return (
              <div key={lvl} className="space-y-1.5">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="font-semibold text-[#090909] flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: LEVEL_COLORS[lvl] }}
                    />
                    {lvl}
                  </span>
                  <span className="font-mono text-[11.5px] text-[#666666]">
                    Before: {pre} → After: <strong className="text-[#090909]">{post}</strong>
                  </span>
                </div>
                <div className="space-y-1">
                  <div className="h-2 w-full bg-[#F4F4F2] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#A3A3A3] rounded-full"
                      style={{ width: `${preW}%` }}
                    />
                  </div>
                  <div className="h-2 w-full bg-[#F4F4F2] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${postW}%`,
                        backgroundColor: LEVEL_COLORS[lvl],
                      }}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </ChartCard>

      {/* Attack Simulation Results */}
      <ChartCard
        title="Attack Simulation Outcomes"
        subtitle="Adversarial re-identification attempts evaluated against sanitised output."
        unit="Vectors · Risk %"
        source="/api/privacy-intelligence + /api/threat-lab"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={!hasAttack}
        emptyTitle="Attack simulation not executed"
        emptyDescription="Run the 7-vector Attack Simulator on a completed job to view blocked vs. exposed outcomes."
        headerRight={
          hasAttack && attackOverview ? (
            <div className="flex items-center gap-2 text-[11px] font-mono">
              <span className="px-2 py-0.5 rounded bg-[#ECF3EC] text-[#166534] border border-[#C6DBC7]">
                Blocked: {attackOverview.blocked}/{attackOverview.total}
              </span>
              {attackOverview.exposed > 0 && (
                <span className="px-2 py-0.5 rounded bg-[#FEF2F2] text-[#991B1B] border border-[#FECACA]">
                  Exposed: {attackOverview.exposed}
                </span>
              )}
            </div>
          ) : null
        }
      >
        <div className="space-y-2.5">
          {attackStrategies.map((s, idx) => {
            const isBlocked = s.status === "BLOCKED";
            const isExposed = s.status === "EXPOSED";
            const barColor = isBlocked
              ? "#166534"
              : isExposed
              ? "#991B1B"
              : "#737373";
            const barWidth = isBlocked
              ? 100
              : Math.min(100, Math.max(8, s.risk_score || 0));

            return (
              <div key={idx} className="space-y-1">
                <div className="flex items-center justify-between gap-2 text-[12px]">
                  <span className="font-medium text-[#090909] truncate">
                    {s.strategy}
                  </span>
                  <span className="font-mono text-[11px] text-[#666666] shrink-0">
                    {s.status} · {s.matched_records} match(es)
                  </span>
                </div>
                <div className="h-2 w-full bg-[#F4F4F2] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${barWidth}%`, backgroundColor: barColor }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </ChartCard>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import type { IdentityGraph } from "@/lib/api";
import { ChartCard } from "./ChartCard";

export interface IdentityContinuityChartProps {
  graph: IdentityGraph | null;
  loading?: boolean;
  error?: string;
  lastUpdated?: number | null;
}

export function IdentityContinuityChart({
  graph,
  loading = false,
  error = "",
  lastUpdated,
}: IdentityContinuityChartProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const measured = graph?.status === "MEASURED";
  const nodes = (graph?.nodes ?? []).slice(0, 18);
  const nodeIndex = new Map<string, number>();
  nodes.forEach((n, i) => nodeIndex.set(n.id, i));

  const visibleEdges = (graph?.edges ?? []).filter(
    (e) => nodeIndex.has(e.source) && nodeIndex.has(e.target)
  );

  // Circular layout for pseudonymous relationship visualization
  const width = 460;
  const height = 270;
  const centerX = width / 2;
  const centerY = height / 2;
  const rx = 155;
  const ry = 95;

  const coords = nodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, nodes.length) - Math.PI / 2;
    return {
      ...n,
      x: centerX + rx * Math.cos(angle),
      y: centerY + ry * Math.sin(angle),
    };
  });

  const qualityBars = [
    {
      label: "Precision",
      val: graph?.precision,
      display: graph?.precision != null ? `${(graph.precision * 100).toFixed(1)}%` : "Not measured",
      pct: graph?.precision != null ? graph.precision * 100 : 0,
      color: "#090909",
    },
    {
      label: "Recall",
      val: graph?.recall,
      display: graph?.recall != null ? `${(graph.recall * 100).toFixed(1)}%` : "Not measured",
      pct: graph?.recall != null ? graph.recall * 100 : 0,
      color: "#444444",
    },
    {
      label: "F0.5 Score",
      val: graph?.f05,
      display: graph?.f05 != null ? `${(graph.f05 * 100).toFixed(1)}%` : "Not measured",
      pct: graph?.f05 != null ? graph.f05 * 100 : 0,
      color: "#166534",
    },
  ];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      {/* Matching Quality & Summary */}
      <ChartCard
        title="Matching Quality & Linkage Summary"
        subtitle="Conservative multi-signal identity resolution metrics (zero raw PII)."
        unit="Score (%)"
        source="/api/identity/clusters"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={!measured}
        emptyTitle="Matching quality not measured"
        emptyDescription="Process a multi-record dataset to evaluate precision, recall, F0.5, and abstentions."
      >
        <div className="space-y-4">
          <div className="space-y-3">
            {qualityBars.map((b) => (
              <div key={b.label} className="space-y-1">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="font-medium text-[#090909]">{b.label}</span>
                  <span className="font-mono text-[12px] font-semibold text-[#090909]">
                    {b.display}
                  </span>
                </div>
                <div className="h-2.5 w-full bg-[#F4F4F2] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(100, Math.max(0, b.pct))}%`,
                      backgroundColor: b.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-[#E5E5E5]">
            <div className="bg-[#F4F4F2] rounded-xl p-3">
              <div className="text-[10px] font-semibold uppercase text-[#666666]">Clusters</div>
              <div className="font-serif-display text-[20px] text-[#090909]">
                {graph?.total_patients ?? 0}
              </div>
            </div>
            <div className="bg-[#F4F4F2] rounded-xl p-3">
              <div className="text-[10px] font-semibold uppercase text-[#666666]">Cross-Org Links</div>
              <div className="font-serif-display text-[20px] text-[#090909]">
                {graph?.cross_hospital_links ?? 0}
              </div>
            </div>
            <div className="bg-[#ECF3EC] rounded-xl p-3">
              <div className="text-[10px] font-semibold uppercase text-[#166534]">False Merges</div>
              <div className="font-serif-display text-[20px] text-[#166534]">
                {graph?.false_merges ?? 0}
              </div>
            </div>
            <div className="bg-[#F4F4F2] rounded-xl p-3">
              <div className="text-[10px] font-semibold uppercase text-[#666666]">Abstentions</div>
              <div className="font-serif-display text-[20px] text-[#090909]">
                {graph?.abstentions ?? 0}
              </div>
            </div>
          </div>
        </div>
      </ChartCard>

      {/* Pseudonymous Relationship Graph */}
      <ChartCard
        title="Pseudonymous Relationship Graph"
        subtitle="Internal pseudonymous nodes and verified vs. uncertain linkage edges."
        unit="Nodes · Edges"
        source="/api/identity/clusters"
        lastUpdated={lastUpdated}
        loading={loading}
        error={error}
        empty={nodes.length === 0}
        emptyTitle="No pseudonymous clusters to render"
        emptyDescription="Process a dataset with multiple records to visualize pseudonymous patient linkage."
        headerRight={
          nodes.length > 0 ? (
            <div className="flex items-center gap-3 text-[11px] text-[#666666]">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-[#090909]" />
                Confirmed
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-3 h-0.5 border-t-2 border-dashed border-[#92400E]" />
                Uncertain
              </span>
            </div>
          ) : null
        }
      >
        <div>
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-auto bg-[#F9F9F8] rounded-xl border border-[#E5E5E5]"
            role="img"
            aria-label="Pseudonymous Identity Relationship Graph"
          >
            {visibleEdges.map((edge, idx) => {
              const sIdx = nodeIndex.get(edge.source);
              const tIdx = nodeIndex.get(edge.target);
              if (sIdx === undefined || tIdx === undefined) return null;
              const s = coords[sIdx];
              const t = coords[tIdx];
              const conf = edge.confidence ?? 1.0;
              const confirmed = conf >= 0.85;
              const highlighted =
                selectedNodeId === edge.source || selectedNodeId === edge.target;
              return (
                <line
                  key={idx}
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  stroke={confirmed ? "#090909" : "#92400E"}
                  strokeWidth={highlighted ? 2.5 : 1.4}
                  strokeDasharray={confirmed ? undefined : "4 3"}
                  opacity={selectedNodeId && !highlighted ? 0.25 : 0.8}
                />
              );
            })}

            {coords.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const isCluster = node.type.toLowerCase().includes("cluster");
              return (
                <g
                  key={node.id}
                  onClick={() =>
                    setSelectedNodeId((prev) => (prev === node.id ? null : node.id))
                  }
                  className="cursor-pointer"
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={isSelected ? 11 : isCluster ? 9 : 7}
                    fill={isCluster ? "#090909" : "#FFFFFF"}
                    stroke="#090909"
                    strokeWidth={2}
                  />
                  <text
                    x={node.x}
                    y={node.y + 19}
                    textAnchor="middle"
                    className="fill-[#444444] text-[9px] font-mono"
                  >
                    {node.label.slice(0, 12)}
                  </text>
                </g>
              );
            })}
          </svg>
          {graph && graph.nodes.length > 18 && (
            <div className="text-[11px] text-[#888888] mt-1.5">
              Showing first 18 of {graph.nodes.length} pseudonymous nodes.
            </div>
          )}
        </div>
      </ChartCard>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api, type IdentityGraph } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";

export default function IdentityContinuityPage() {
  const [graph, setGraph] = useState<IdentityGraph | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.identityGraph().then(setGraph).catch((e) => setError(e.message));
  }, []);

  const measured = graph?.status === "MEASURED";

  const stats = [
    { label: "Total Patients", value: measured ? String(graph.total_patients) : "Not measured" },
    { label: "Cross-Hospital Links", value: measured ? String(graph.cross_hospital_links) : "Not measured" },
    { label: "Precision", value: graph?.precision != null ? graph.precision.toFixed(2) : "Not measured" },
    { label: "Recall", value: graph?.recall != null ? graph.recall.toFixed(2) : "Not measured" },
    { label: "F0.5 Score", value: graph?.f05 != null ? graph.f05.toFixed(2) : "Not measured" },
    { label: "False Merges", value: measured ? String(graph.false_merges) : "Not measured" },
    { label: "Abstentions", value: measured ? String(graph.abstentions) : "Not measured" },
    { label: "Conflicts", value: measured ? String(graph.conflicts) : "Not measured" },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="07 · PSEUDONYMOUS RECORD LINKAGE"
        title="Identity Continuity"
        subtitle="Cross-hospital patient resolution using pseudonymous evidence only. Name similarity alone never merges records."
      />

      {error && <ErrorState message={error} />}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {stats.map((m) => (
          <div key={m.label} className="bg-white border border-[#DADADA] rounded-2xl p-5">
            <div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-[#888888] mb-2">
              {m.label}
            </div>
            <div className="font-serif-display text-[26px] leading-none text-[#090909]">
              {m.value}
            </div>
          </div>
        ))}
      </div>

      {!graph || (graph.nodes.length === 0 && graph.edges.length === 0) ? (
        <EmptyState
          title="No identity clusters measured"
          description="Process a multi-record dataset to inspect pseudonymous patient clusters and linkage edges."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#E5E5E5]">
              <h2 className="text-[15px] font-semibold text-[#090909]">
                Pseudonym Nodes ({graph.nodes.length})
              </h2>
            </div>
            <div className="max-h-[360px] overflow-y-auto divide-y divide-[#E5E5E5]">
              {graph.nodes.map((n) => (
                <div key={n.id} className="px-5 py-3 flex items-center justify-between gap-3">
                  <span className="text-[12.5px] font-mono text-[#090909] truncate">{n.label}</span>
                  <span className="text-[11px] px-2 py-0.5 rounded bg-[#F4F4F2] border border-[#E5E5E5] text-[#666666]">
                    {n.type}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-[#E5E5E5]">
              <h2 className="text-[15px] font-semibold text-[#090909]">
                Verified Linkage Edges ({graph.edges.length})
              </h2>
            </div>
            <div className="max-h-[360px] overflow-y-auto divide-y divide-[#E5E5E5]">
              {graph.edges.map((e, i) => (
                <div key={i} className="px-5 py-3 flex items-center justify-between gap-3 text-[12px]">
                  <span className="font-mono text-[#090909] truncate">
                    {e.source} → {e.target}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-[#090909] text-white text-[11px] font-semibold">
                    {e.confidence != null ? `${(e.confidence * 100).toFixed(0)}%` : "LINKED"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api, type IdentityGraph } from "@/lib/api";
import { Network, AlertTriangle } from "lucide-react";

export default function IdentityContinuityPage() {
  const [graph, setGraph] = useState<IdentityGraph | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.identityGraph().then(setGraph).catch((e) => setError(e.message));
  }, []);

  const measured = graph?.status === "MEASURED";

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Identity Continuity
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Cross-hospital patient identity resolution graph using pseudonymous evidence only. Name similarity alone never merges records.
        </p>
      </div>

      {error && (
        <div
          style={{
            padding: "12px 16px",
            background: "#FFFBF0",
            border: "1.5px solid #E6D5A0",
            borderRadius: 8,
            fontSize: 13,
            color: "#7A5C00",
            marginBottom: 20,
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <AlertTriangle size={15} />
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(175px, 1fr))", gap: 14, marginBottom: 28 }}>
        {[
          { label: "Total Patients", value: measured ? graph.total_patients : "Not measured" },
          { label: "Cross-Hospital Links", value: measured ? graph.cross_hospital_links : "Not measured" },
          { label: "Precision", value: graph?.precision != null ? graph.precision.toFixed(2) : "Not measured" },
          { label: "Recall", value: graph?.recall != null ? graph.recall.toFixed(2) : "Not measured" },
          { label: "F0.5 Score", value: graph?.f05 != null ? graph.f05.toFixed(2) : "Not measured" },
          { label: "False Merges", value: measured ? graph.false_merges : "Not measured" },
          { label: "Abstentions", value: measured ? graph.abstentions : "Not measured" },
          { label: "Conflicts", value: measured ? graph.conflicts : "Not measured" },
        ].map((m) => (
          <div key={m.label} style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "16px 18px" }}>
            <div style={{ fontSize: 11.5, color: "#777777", fontWeight: 500, marginBottom: 6 }}>{m.label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: "#050505", letterSpacing: "-0.5px" }}>{m.value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
              Pseudonym Nodes ({graph?.nodes?.length ?? 0})
            </span>
            <Network size={14} color="#777777" />
          </div>
          {graph?.nodes && graph.nodes.length > 0 ? (
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              {graph.nodes.map((n) => (
                <div key={n.id} style={{ padding: "10px 20px", borderBottom: "1px solid #F5F5F5", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 12.5, fontWeight: 500, color: "#050505", fontFamily: "monospace" }}>{n.label}</span>
                  <span style={{ fontSize: 11, padding: "2px 7px", background: "#F2F2F2", borderRadius: 4, color: "#555555" }}>{n.type}</span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#777777" }}>
              No identity nodes measured yet.
            </div>
          )}
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
          <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
            Verified Linkage Edges ({graph?.edges?.length ?? 0})
          </div>
          {graph?.edges && graph.edges.length > 0 ? (
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              {graph.edges.map((e, i) => (
                <div key={i} style={{ padding: "10px 20px", borderBottom: "1px solid #F5F5F5", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12 }}>
                  <span style={{ color: "#050505", fontFamily: "monospace" }}>{e.source} → {e.target}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 7px", background: "#050505", color: "#FFFFFF", borderRadius: 4 }}>
                    {e.confidence != null ? `${(e.confidence * 100).toFixed(0)}%` : "LINKED"}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#777777" }}>
              No linkage edges measured yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

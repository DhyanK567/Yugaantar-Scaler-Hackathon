"use client";
import { useEffect, useState } from "react";
import { api, type IdentityGraph, type DashboardData } from "@/lib/api";
import { Network, AlertTriangle } from "lucide-react";

export default function IdentityContinuityPage() {
  const [graph, setGraph] = useState<IdentityGraph | null>(null);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.identityGraph(), api.dashboard()])
      .then(([g, d]) => {
        setGraph(g);
        setDash(d);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Identity Continuity
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Cross-hospital patient identity resolution graph using pseudonymised evidence.
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

      {/* Metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(190px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        {[
          { label: "Total Patients", value: graph?.total_patients ?? "—" },
          { label: "Cross-Hospital Links", value: graph?.cross_hospital_links ?? "—" },
          {
            label: "Precision",
            value: dash?.identity_precision != null ? dash.identity_precision.toFixed(2) : "—",
          },
          {
            label: "Recall",
            value: dash?.identity_recall != null ? dash.identity_recall.toFixed(2) : "—",
          },
          {
            label: "F0.5 Score",
            value: dash?.identity_f05 != null ? dash.identity_f05.toFixed(2) : "—",
          },
          { label: "False Merges", value: dash?.false_merges ?? "—" },
        ].map((m) => (
          <div
            key={m.label}
            style={{
              background: "#FFFFFF",
              border: "1.5px solid #DCDCDC",
              borderRadius: 10,
              padding: "18px 20px",
            }}
          >
            <div style={{ fontSize: 12, color: "#777777", fontWeight: 500, marginBottom: 6 }}>
              {m.label}
            </div>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px" }}>
              {m.value}
            </div>
          </div>
        ))}
      </div>

      {/* Graph table */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 20px",
              borderBottom: "1px solid #EEEEEE",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
              Pseudonym Nodes ({graph?.nodes?.length ?? 0})
            </span>
            <Network size={14} color="#777777" />
          </div>
          {graph?.nodes && graph.nodes.length > 0 ? (
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              {graph.nodes.map((n) => (
                <div
                  key={n.id}
                  style={{
                    padding: "10px 20px",
                    borderBottom: "1px solid #F5F5F5",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontSize: 13, fontWeight: 500, color: "#050505" }}>{n.label}</span>
                  <span
                    style={{
                      fontSize: 11,
                      padding: "2px 7px",
                      background: "#F2F2F2",
                      borderRadius: 4,
                      color: "#555555",
                    }}
                  >
                    {n.type}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
              No identity nodes available.
            </div>
          )}
        </div>

        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "14px 20px",
              borderBottom: "1px solid #EEEEEE",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
              Verified Linkage Edges ({graph?.edges?.length ?? 0})
            </span>
          </div>
          {graph?.edges && graph.edges.length > 0 ? (
            <div style={{ maxHeight: 360, overflowY: "auto" }}>
              {graph.edges.map((e, i) => (
                <div
                  key={i}
                  style={{
                    padding: "10px 20px",
                    borderBottom: "1px solid #F5F5F5",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    fontSize: 12.5,
                  }}
                >
                  <span style={{ color: "#050505", fontFamily: "monospace" }}>
                    {e.source} → {e.target}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 600,
                      padding: "2px 7px",
                      background: "#050505",
                      color: "#FFFFFF",
                      borderRadius: 4,
                    }}
                  >
                    {(e.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
              No linkage edges available.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

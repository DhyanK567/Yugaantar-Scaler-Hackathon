"use client";
import { useEffect, useState } from "react";
import { api, type PrivacyIntelligence, type ThreatLabData } from "@/lib/api";
import { Brain, AlertTriangle } from "lucide-react";

function BreakdownCard({
  title,
  entries,
}: {
  title: string;
  entries?: Record<string, number>;
}) {
  const items = entries ? Object.entries(entries) : [];
  const max = items.reduce((m, [, v]) => Math.max(m, v), 1);

  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "1.5px solid #DCDCDC",
        borderRadius: 10,
        padding: 22,
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 600, color: "#050505", marginBottom: 18 }}>
        {title}
      </div>
      {items.length === 0 ? (
        <div style={{ fontSize: 13, color: "#AAAAAA", padding: "24px 0", textAlign: "center" }}>
          No telemetry available yet.
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {items.map(([key, val]) => (
            <div key={key}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 5 }}>
                <span style={{ color: "#050505", fontWeight: 500 }}>{key}</span>
                <span style={{ color: "#777777" }}>{val.toLocaleString()}</span>
              </div>
              <div style={{ height: 6, background: "#F2F2F2", borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    width: `${Math.round((val / max) * 100)}%`,
                    background: "#050505",
                    borderRadius: 3,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PrivacyIntelligencePage() {
  const [intel, setIntel] = useState<PrivacyIntelligence | null>(null);
  const [threat, setThreat] = useState<ThreatLabData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.privacyIntelligence(), api.threatLab()])
      .then(([i, t]) => {
        setIntel(i);
        setThreat(t);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Privacy Intelligence
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Identifier distribution, multilingual coverage and re-identification risk posture.
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

      {/* Summary banner */}
      <div
        style={{
          background: "#050505",
          color: "#FFFFFF",
          borderRadius: 10,
          padding: "22px 26px",
          marginBottom: 24,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Brain size={22} color="#FFFFFF" />
          <div>
            <div style={{ fontSize: 12, color: "#888888", textTransform: "uppercase", letterSpacing: "0.5px" }}>
              Aggregate Re-Identification Risk Score
            </div>
            <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-1px" }}>
              {threat?.risk_score != null ? `${threat.risk_score}` : "—"}
            </div>
          </div>
        </div>
        {intel?.top_identifiers && intel.top_identifiers.length > 0 && (
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {intel.top_identifiers.map((id) => (
              <span
                key={id}
                style={{
                  padding: "4px 10px",
                  background: "#1E1E1E",
                  border: "1px solid #333333",
                  borderRadius: 5,
                  fontSize: 12,
                  color: "#E6E6E6",
                }}
              >
                {id}
              </span>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: 20 }}>
        <BreakdownCard title="PII Category Breakdown" entries={intel?.pii_breakdown} />
        <BreakdownCard title="Language Distribution" entries={intel?.language_distribution} />
        <BreakdownCard title="Risk Distribution" entries={intel?.risk_distribution} />
      </div>
    </div>
  );
}

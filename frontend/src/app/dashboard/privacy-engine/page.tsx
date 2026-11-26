"use client";
import { useEffect, useState } from "react";
import { api, type DashboardData, type Settings } from "@/lib/api";
import { Shield, Cpu, Lock, CheckCircle2, ArrowRight, AlertTriangle } from "lucide-react";

const PIPELINE_STAGES = [
  {
    step: "01",
    title: "Streaming Ingestion",
    desc: "Memory-bounded parsing for CSV, TSV, JSON, FHIR R4 bundles and free-text notes.",
  },
  {
    step: "02",
    title: "Multilingual PII Detection",
    desc: "Deterministic regex, phonetic and script-aware identifier extraction across 11 languages.",
  },
  {
    step: "03",
    title: "Cross-Hospital Identity Linking",
    desc: "Conservative multi-evidence blocking and clustering with zero false merges.",
  },
  {
    step: "04",
    title: "HMAC-SHA256 Pseudonymisation",
    desc: "Deterministic keyed pseudonym replacement using RAKSHA_SECRET.",
  },
  {
    step: "05",
    title: "Clinical Integrity & Passport",
    desc: "Validates lab/diagnosis preservation and emits verifiable output contracts.",
  },
];

export default function PrivacyEnginePage() {
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.dashboard(), api.settings()])
      .then(([d, s]) => {
        setDash(d);
        setSettings(s);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Privacy Engine
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Offline, CPU-only deterministic sanitisation pipeline architecture and runtime state.
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

      {/* Runtime summary */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Execution Mode</span>
            <Cpu size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>CPU-Only · Offline</div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>Zero LLMs · Zero cloud calls</div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Secret Key Status</span>
            <Lock size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>
            {settings ? (settings.raksha_secret_set ? "Configured" : "Not Set") : "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>RAKSHA_SECRET HMAC key</div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Sanitised Files</span>
            <Shield size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>
            {dash?.sanitised_files ?? "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>
            {dash ? `${dash.quarantined_files ?? 0} quarantined` : "Awaiting backend"}
          </div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Multilingual NLP</span>
            <CheckCircle2 size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>
            {settings ? (settings.multilingual_enabled ? "Enabled" : "Disabled") : "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>
            Output format: {settings?.output_format ?? "—"}
          </div>
        </div>
      </div>

      {/* Pipeline workflow */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          padding: 24,
          marginBottom: 28,
        }}
      >
        <div style={{ fontSize: 15, fontWeight: 600, color: "#050505", marginBottom: 20 }}>
          5-Stage Deterministic Sanitisation Pipeline
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))", gap: 14 }}>
          {PIPELINE_STAGES.map((stage, idx) => (
            <div
              key={stage.step}
              style={{
                background: "#F2F2F2",
                border: "1px solid #E6E6E6",
                borderRadius: 8,
                padding: 16,
                position: "relative",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    background: "#050505",
                    color: "#FFFFFF",
                    padding: "2px 7px",
                    borderRadius: 4,
                  }}
                >
                  {stage.step}
                </span>
                {idx < PIPELINE_STAGES.length - 1 && <ArrowRight size={13} color="#777777" />}
              </div>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "#050505", marginBottom: 6 }}>
                {stage.title}
              </div>
              <div style={{ fontSize: 12, color: "#666666", lineHeight: 1.5 }}>{stage.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent jobs inspection */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Recent Pipeline Executions
        </div>
        {dash?.recent_jobs && dash.recent_jobs.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Job ID", "Status", "Files", "Records", "PII Detected", "Created"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 20px",
                      textAlign: "left",
                      fontSize: 11.5,
                      fontWeight: 600,
                      color: "#777777",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dash.recent_jobs.map((j) => (
                <tr key={j.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "12px 20px", fontSize: 13, fontWeight: 500, color: "#050505" }}>
                    {j.id}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 12, textTransform: "uppercase", fontWeight: 600 }}>
                    {j.status}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, color: "#555555" }}>
                    {j.file_count ?? "—"}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, color: "#555555" }}>
                    {j.records_processed ?? "—"}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, color: "#555555" }}>
                    {j.pii_detected ?? "—"}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 12, color: "#777777" }}>
                    {new Date(j.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: "40px 20px", textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
            No pipeline executions recorded yet.
          </div>
        )}
      </div>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api, type JobRecord, type SettingsData } from "@/lib/api";
import { Shield, Cpu, Lock, CheckCircle2, ArrowRight, AlertTriangle } from "lucide-react";

const PIPELINE_STAGES = [
  { step: "01", title: "VALIDATING", desc: "Checks dataset readability, formats, and byte integrity." },
  { step: "02", title: "PROCESSING", desc: "Executes offline deterministic starter/main.py privacy engine." },
  { step: "03", title: "PRIVACY_ANALYSIS", desc: "Measures PII detection, canary containment, and residual risk." },
  { step: "04", title: "CLINICAL_VALIDATION", desc: "Verifies lab values, units, and FHIR R4 bundle integrity." },
  { step: "05", title: "SECURITY_VALIDATION", desc: "Runs 7-vector attack simulator & emits Privacy Passport." },
];

export default function PrivacyEnginePage() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.jobs(), api.settings()])
      .then(([j, s]) => {
        setJobs(j);
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
          Offline, CPU-only deterministic sanitisation pipeline architecture and persistent job history.
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16, marginBottom: 28 }}>
        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Execution Mode</span>
            <Cpu size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>CPU-Only · Offline</div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>Decoupled from web auth</div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>RAKSHA_SECRET</span>
            <Lock size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>
            {settings ? (settings.raksha_secret_set ? "Configured" : "Fallback Practice Key") : "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>HMAC-SHA256 pseudonym key</div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "18px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Total Jobs</span>
            <Shield size={15} color="#050505" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "#050505" }}>{jobs.length}</div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>Persistent SQLite history</div>
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
            Output: {settings?.output_format ?? "—"}
          </div>
        </div>
      </div>

      {/* Pipeline stages */}
      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: 24, marginBottom: 28 }}>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#050505", marginBottom: 20 }}>
          Connected Processing Lifecycle
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 14 }}>
          {PIPELINE_STAGES.map((stage, idx) => (
            <div key={stage.step} style={{ background: "#F2F2F2", border: "1px solid #E6E6E6", borderRadius: 8, padding: 16 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <span style={{ fontSize: 11, fontWeight: 700, background: "#050505", color: "#FFFFFF", padding: "2px 7px", borderRadius: 4 }}>
                  {stage.step}
                </span>
                {idx < PIPELINE_STAGES.length - 1 && <ArrowRight size={13} color="#777777" />}
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#050505", marginBottom: 6 }}>{stage.title}</div>
              <div style={{ fontSize: 12, color: "#666666", lineHeight: 1.5 }}>{stage.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Jobs table */}
      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Processing Jobs
        </div>
        {jobs.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Job ID", "Dataset", "Stage / Status", "Release Decision", "Files", "Records", "Created"].map((h) => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11.5, color: "#777777" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontFamily: "monospace", color: "#050505" }}>{j.id}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13, color: "#333333" }}>{j.dataset_name || j.input_name || "—"}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontWeight: 600 }}>{j.status}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontWeight: 600 }}>{j.release_decision || "PENDING"}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13, color: "#555555" }}>{j.files_total ?? 0}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13, color: "#555555" }}>{j.records_processed ?? 0}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, color: "#777777" }}>
                    {new Date(j.created_at * 1000).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: "40px 20px", textAlign: "center", fontSize: 13, color: "#777777" }}>
            No pipeline executions recorded yet.
          </div>
        )}
      </div>
    </div>
  );
}

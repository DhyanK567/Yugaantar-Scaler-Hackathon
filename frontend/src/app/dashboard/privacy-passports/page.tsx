"use client";
import { useEffect, useState } from "react";
import { api, type DashboardData } from "@/lib/api";
import { FileKey2, Download, CheckCircle2, AlertTriangle } from "lucide-react";

export default function PrivacyPassportsPage() {
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .dashboard()
      .then(setDash)
      .catch((e) => setError(e.message));
  }, []);

  const jobs = dash?.recent_jobs ?? [];

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Privacy Passports
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Cryptographically verifiable compliance manifests generated for every sanitised dataset.
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

      {jobs.length === 0 ? (
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            padding: "56px 24px",
            textAlign: "center",
            color: "#777777",
            fontSize: 13.5,
          }}
        >
          No Privacy Passports generated yet. Run a sanitisation job under Datasets to issue a passport.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 16,
          }}
        >
          {jobs.map((job) => (
            <div
              key={job.id}
              style={{
                background: "#FFFFFF",
                border: "1.5px solid #DCDCDC",
                borderRadius: 10,
                padding: 22,
                display: "flex",
                flexDirection: "column",
                gap: 14,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileKey2 size={18} color="#050505" />
                  <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
                    Passport {job.id.slice(0, 8)}
                  </span>
                </div>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "3px 8px",
                    borderRadius: 4,
                    background: job.status === "done" ? "#050505" : "#E6E6E6",
                    color: job.status === "done" ? "#FFFFFF" : "#050505",
                  }}
                >
                  <CheckCircle2 size={11} />
                  {job.status.toUpperCase()}
                </span>
              </div>

              <div style={{ fontSize: 12.5, color: "#666666", lineHeight: 1.6 }}>
                <div>Records: {job.records_processed ?? "—"}</div>
                <div>Files: {job.file_count ?? "—"}</div>
                <div>Issued: {new Date(job.created_at).toLocaleString()}</div>
              </div>

              {job.status === "done" && (
                <a
                  href={api.downloadJob(job.id)}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    padding: "9px 14px",
                    background: "#F2F2F2",
                    border: "1.5px solid #DCDCDC",
                    borderRadius: 7,
                    fontSize: 13,
                    fontWeight: 500,
                    color: "#050505",
                    textDecoration: "none",
                  }}
                >
                  <Download size={14} />
                  Download Sanitised Bundle
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

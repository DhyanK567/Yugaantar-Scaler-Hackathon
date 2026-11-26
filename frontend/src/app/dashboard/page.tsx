"use client";
import { useEffect, useState } from "react";
import { api, type DashboardData } from "@/lib/api";
import {
  Shield,
  FileText,
  AlertTriangle,
  HeartPulse,
  Users,
  CheckCircle2,
  Clock,
  TrendingUp,
} from "lucide-react";

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  ok,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  ok?: boolean;
}) {
  return (
    <div
      style={{
        background: "#FFFFFF",
        border: "1.5px solid #DCDCDC",
        borderRadius: 10,
        padding: "20px 22px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>{label}</span>
        <div
          style={{
            width: 30,
            height: 30,
            background: "#F2F2F2",
            borderRadius: 7,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon size={15} strokeWidth={1.5} color="#050505" />
        </div>
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color: "#050505", letterSpacing: "-1px" }}>
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: 11.5,
            color: ok === true ? "#2D7A2D" : ok === false ? "#CC3333" : "#777777",
            fontWeight: 500,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      {/* Header */}
      <div style={{ marginBottom: 28 }}>
        <h1
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: "#050505",
            letterSpacing: "-0.8px",
            marginBottom: 4,
          }}
        >
          Privacy Dashboard
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Real-time overview of your healthcare data privacy pipeline.
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
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <AlertTriangle size={16} />
          Backend unavailable — start the FastAPI server on port 8000.{" "}
          <code style={{ fontSize: 11, background: "#F5EDD0", padding: "1px 6px", borderRadius: 3 }}>
            uvicorn backend.main:app --reload
          </code>
        </div>
      )}

      {/* Stats grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <StatCard
          label="Files Processed"
          value={data?.sanitised_files ?? "—"}
          sub={data ? `+ ${data.quarantined_files ?? 0} quarantined` : undefined}
          icon={FileText}
        />
        <StatCard
          label="Records Processed"
          value={data?.total_records ?? "—"}
          icon={Users}
        />
        <StatCard
          label="PII Detected"
          value={data?.pii_detected ?? "—"}
          sub={data?.pii_detected === 0 ? "✓ Zero leakage" : "Review required"}
          ok={data?.pii_detected === 0}
          icon={Shield}
        />
        <StatCard
          label="Clinical Preserved"
          value={
            data?.clinical_preserved != null
              ? `${data.clinical_preserved}`
              : "—"
          }
          sub="Lab values intact"
          ok={true}
          icon={HeartPulse}
        />
        <StatCard
          label="Identity Precision"
          value={
            data?.identity_precision != null
              ? data.identity_precision.toFixed(2)
              : "—"
          }
          sub="No false merges"
          ok={data?.false_merges === 0}
          icon={TrendingUp}
        />
        <StatCard
          label="Canary Leaks"
          value={data?.canary_leaks ?? "—"}
          sub={data?.canary_leaks === 0 ? "✓ All canaries contained" : "⚠ Canary escaped"}
          ok={data?.canary_leaks === 0}
          icon={CheckCircle2}
        />
      </div>

      {/* Recent jobs + Audit events */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Recent jobs */}
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
              padding: "16px 20px",
              borderBottom: "1px solid #EEEEEE",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>Recent Jobs</span>
            <Clock size={14} color="#777777" />
          </div>
          <div>
            {data?.recent_jobs && data.recent_jobs.length > 0 ? (
              data.recent_jobs.slice(0, 6).map((job) => (
                <div
                  key={job.id}
                  style={{
                    padding: "12px 20px",
                    borderBottom: "1px solid #EEEEEE",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500, color: "#050505" }}>
                      Job {job.id.slice(0, 8)}
                    </div>
                    <div style={{ fontSize: 11.5, color: "#777777", marginTop: 2 }}>
                      {new Date(job.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "3px 8px",
                      background:
                        job.status === "done"
                          ? "#050505"
                          : job.status === "running"
                          ? "#E6E6E6"
                          : "#F2F2F2",
                      color:
                        job.status === "done"
                          ? "#FFFFFF"
                          : "#050505",
                      borderRadius: 4,
                      fontSize: 10.5,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                    }}
                  >
                    {job.status}
                  </div>
                </div>
              ))
            ) : (
              <div
                style={{
                  padding: "32px 20px",
                  textAlign: "center",
                  fontSize: 13,
                  color: "#AAAAAA",
                }}
              >
                No jobs yet. Upload a dataset to get started.
              </div>
            )}
          </div>
        </div>

        {/* Audit events */}
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
              padding: "16px 20px",
              borderBottom: "1px solid #EEEEEE",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>Audit Events</span>
            <FileText size={14} color="#777777" />
          </div>
          <div>
            {data?.audit_events && data.audit_events.length > 0 ? (
              data.audit_events.slice(0, 6).map((ev) => (
                <div
                  key={ev.id}
                  style={{
                    padding: "12px 20px",
                    borderBottom: "1px solid #EEEEEE",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                  }}
                >
                  <div
                    style={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      background:
                        ev.severity === "high"
                          ? "#CC3333"
                          : ev.severity === "medium"
                          ? "#AA8800"
                          : "#050505",
                      flexShrink: 0,
                      marginTop: 5,
                    }}
                  />
                  <div>
                    <div style={{ fontSize: 12.5, color: "#050505", fontWeight: 500 }}>
                      {ev.event_type}
                    </div>
                    <div style={{ fontSize: 11.5, color: "#777777", marginTop: 2 }}>
                      {ev.description}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div
                style={{
                  padding: "32px 20px",
                  textAlign: "center",
                  fontSize: 13,
                  color: "#AAAAAA",
                }}
              >
                No audit events yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  ApiError,
  type DashboardOverview,
  type MetricCardData,
  type MetricStatus,
} from "@/lib/api";
import {
  Shield,
  FileText,
  AlertTriangle,
  HeartPulse,
  Users,
  CheckCircle2,
  TrendingUp,
  ArrowUpRight,
  Lock,
} from "lucide-react";

function StatusPill({ status }: { status: MetricStatus | string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    PASS: { bg: "#050505", color: "#FFFFFF", label: "PASS" },
    APPROVED: { bg: "#050505", color: "#FFFFFF", label: "APPROVED" },
    COMPLETED: { bg: "#050505", color: "#FFFFFF", label: "COMPLETED" },
    WARNING: { bg: "#FFF5D6", color: "#8A6500", label: "WARNING" },
    COMPLETED_WITH_WARNINGS: { bg: "#FFF5D6", color: "#8A6500", label: "WARNINGS" },
    QUARANTINED: { bg: "#FFF5D6", color: "#8A6500", label: "QUARANTINED" },
    FAILED: { bg: "#FFE5E5", color: "#CC3333", label: "FAILED" },
    BLOCKED: { bg: "#FFE5E5", color: "#CC3333", label: "BLOCKED" },
    NOT_RUN: { bg: "#F2F2F2", color: "#777777", label: "NOT_RUN" },
    NOT_MEASURED: { bg: "#F2F2F2", color: "#777777", label: "NOT_MEASURED" },
  };
  const s = map[status] ?? { bg: "#E6E6E6", color: "#050505", label: status };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 7px",
        background: s.bg,
        color: s.color,
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.4px",
      }}
    >
      {s.label}
    </span>
  );
}

function MetricCard({
  label,
  metric,
  href,
  icon: Icon,
}: {
  label: string;
  metric?: MetricCardData;
  href: string;
  icon: React.ElementType;
}) {
  return (
    <Link
      href={href}
      style={{
        background: "#FFFFFF",
        border: "1.5px solid #DCDCDC",
        borderRadius: 10,
        padding: "18px 20px",
        display: "flex",
        flexDirection: "column",
        gap: 10,
        textDecoration: "none",
        color: "inherit",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>{label}</span>
        <div
          style={{
            width: 28,
            height: 28,
            background: "#F2F2F2",
            borderRadius: 7,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Icon size={14} strokeWidth={1.6} color="#050505" />
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#050505", letterSpacing: "-0.7px" }}>
          {metric ? metric.display : "Loading…"}
        </div>
        {metric && <StatusPill status={metric.status} />}
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6 }}>
        <span style={{ fontSize: 11.5, color: "#666666" }}>
          {metric ? metric.description : "Fetching telemetry"}
        </span>
        <ArrowUpRight size={13} color="#777777" />
      </div>
    </Link>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [error, setError] = useState("");
  const [unauth, setUnauth] = useState(false);

  useEffect(() => {
    api
      .dashboard()
      .then(setData)
      .catch((e: unknown) => {
        if (e instanceof ApiError && e.status === 401) {
          setUnauth(true);
        } else {
          setError(e instanceof Error ? e.message : String(e));
        }
      });
  }, []);

  if (unauth) {
    return (
      <div style={{ padding: "64px 36px", maxWidth: 520, margin: "0 auto", textAlign: "center" }}>
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 12,
            padding: 36,
          }}
        >
          <Lock size={28} color="#050505" style={{ margin: "0 auto 14px" }} />
          <h1 style={{ fontSize: 20, fontWeight: 700, color: "#050505", marginBottom: 8 }}>
            Sign in required
          </h1>
          <p style={{ fontSize: 13.5, color: "#666666", marginBottom: 22 }}>
            Authenticate with Email OTP or Google to access organisation-scoped privacy telemetry.
          </p>
          <Link
            href="/login"
            style={{
              display: "inline-block",
              padding: "10px 24px",
              background: "#050505",
              color: "#FFFFFF",
              borderRadius: 7,
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            Go to Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
            Privacy Dashboard
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Evidence-based privacy, identity continuity, and clinical integrity telemetry.
          </p>
        </div>
        {data && (
          <div style={{ fontSize: 11.5, color: "#777777" }}>
            Updated {new Date(data.freshness * 1000).toLocaleTimeString()}
          </div>
        )}
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
          {error}
        </div>
      )}

      {/* Privacy Health Summary */}
      {data && (
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            padding: "18px 22px",
            marginBottom: 24,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
            gap: 16,
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#777777", textTransform: "uppercase", marginBottom: 6 }}>
              Overall Release Readiness
            </div>
            <StatusPill status={data.privacy_health.overall_readiness} />
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#777777", marginBottom: 3 }}>Latest Processing Job</div>
            <div style={{ fontSize: 13.5, fontWeight: 600, color: "#050505" }}>
              {data.privacy_health.latest_job_id
                ? `${data.privacy_health.latest_job_id.slice(0, 14)} (${data.privacy_health.latest_job_status})`
                : "No jobs run"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#777777", marginBottom: 3 }}>Critical Risks</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: data.privacy_health.critical_unresolved_risks > 0 ? "#CC3333" : "#050505" }}>
              {data.privacy_health.critical_unresolved_risks}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#777777", marginBottom: 3 }}>Pending Checks</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#050505" }}>
              {data.privacy_health.pending_checks}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#777777", marginBottom: 3 }}>Latest Verification</div>
            <div style={{ fontSize: 12.5, color: "#555555" }}>
              {data.privacy_health.latest_verified_at
                ? new Date(data.privacy_health.latest_verified_at * 1000).toLocaleString()
                : "Not verified yet"}
            </div>
          </div>
        </div>
      )}

      {/* 6 Clickable Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <MetricCard
          label="Files Processed"
          metric={data?.metrics.files_processed}
          href="/dashboard/datasets"
          icon={FileText}
        />
        <MetricCard
          label="Records Processed"
          metric={data?.metrics.records_processed}
          href="/dashboard/datasets"
          icon={Users}
        />
        <MetricCard
          label="PII Detected"
          metric={data?.metrics.pii_detected}
          href="/dashboard/privacy-intelligence"
          icon={Shield}
        />
        <MetricCard
          label="Clinical Values Preserved"
          metric={data?.metrics.clinical_preserved}
          href="/dashboard/clinical-integrity"
          icon={HeartPulse}
        />
        <MetricCard
          label="Identity Precision"
          metric={data?.metrics.identity_precision}
          href="/dashboard/identity-continuity"
          icon={TrendingUp}
        />
        <MetricCard
          label="Canary Leaks"
          metric={data?.metrics.canary_leaks}
          href="/dashboard/attack-simulator"
          icon={CheckCircle2}
        />
      </div>

      {/* Recent Jobs & Audit Events */}
      <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 20 }}>
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
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>Recent Jobs</span>
            <Link href="/dashboard/privacy-engine" style={{ fontSize: 12, color: "#555555", textDecoration: "none" }}>
              View all →
            </Link>
          </div>
          {data?.recent_jobs && data.recent_jobs.length > 0 ? (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                  {["Job", "Dataset", "Status", "Release", "Action"].map((h) => (
                    <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 11, color: "#777777" }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.recent_jobs.slice(0, 6).map((job) => (
                  <tr key={job.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                    <td style={{ padding: "10px 14px", fontSize: 12, fontFamily: "monospace", color: "#050505" }}>
                      {job.id.slice(0, 12)}
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: 12.5, color: "#333333" }}>
                      {job.dataset_name || job.input_name || "—"}
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <StatusPill status={job.status} />
                    </td>
                    <td style={{ padding: "10px 14px" }}>
                      <StatusPill status={job.release_decision || "PENDING"} />
                    </td>
                    <td style={{ padding: "10px 14px", fontSize: 12 }}>
                      <Link href="/dashboard/privacy-passports" style={{ color: "#050505", fontWeight: 500, textDecoration: "none" }}>
                        Inspect
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ padding: "36px 20px", textAlign: "center", fontSize: 13, color: "#777777" }}>
              No processing jobs yet. Upload a dataset to run the pipeline.
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
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>Audit Events</span>
            <Link href="/dashboard/audit" style={{ fontSize: 12, color: "#555555", textDecoration: "none" }}>
              View trail →
            </Link>
          </div>
          {data?.audit_events && data.audit_events.length > 0 ? (
            data.audit_events.slice(0, 6).map((ev) => (
              <div
                key={ev.id}
                style={{
                  padding: "11px 18px",
                  borderBottom: "1px solid #EEEEEE",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 10,
                }}
              >
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: "#050505" }}>
                    {ev.action}
                  </div>
                  <div style={{ fontSize: 11.5, color: "#666666" }}>
                    {ev.actor_email || "system"} · {ev.resource_type}
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <StatusPill status={ev.outcome} />
                  <div style={{ fontSize: 10.5, color: "#888888", marginTop: 3 }}>
                    {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div style={{ padding: "36px 20px", textAlign: "center", fontSize: 13, color: "#777777" }}>
              No audit events recorded yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api, type PrivacyIntelligence } from "@/lib/api";
import { Brain, AlertTriangle, Download } from "lucide-react";

export default function PrivacyIntelligencePage() {
  const [intel, setIntel] = useState<PrivacyIntelligence | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.privacyIntelligence().then(setIntel).catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Privacy Intelligence
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Measured PII detection, residual leakage assessments, and canary containment status.
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

      {/* Summary */}
      <div
        style={{
          background: "#050505",
          color: "#FFFFFF",
          borderRadius: 10,
          padding: "22px 26px",
          marginBottom: 24,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 16,
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Brain size={22} color="#FFFFFF" />
          <div>
            <div style={{ fontSize: 11, color: "#888888", textTransform: "uppercase" }}>Status</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{intel?.status ?? "—"}</div>
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#888888", textTransform: "uppercase" }}>Total PII Detected</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>
            {intel?.status === "MEASURED" ? intel.total_pii_detected : "Not measured"}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#888888", textTransform: "uppercase" }}>Residual Leakage</div>
          <div style={{ fontSize: 22, fontWeight: 700 }}>
            {intel?.status === "MEASURED" ? intel.total_residual_leakage : "Not measured"}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#888888", textTransform: "uppercase" }}>Canary Containment</div>
          <div style={{ fontSize: 20, fontWeight: 700 }}>{intel?.canary_status ?? "NOT_RUN"}</div>
        </div>
      </div>

      {/* Assessments table */}
      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Measured Privacy Assessments ({intel?.assessments?.length ?? 0})
        </div>
        {intel && intel.assessments.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Assessment ID", "Job ID", "PII Detected", "Residual Leaks", "Canary", "QI Risk", "Release Eligible", ""].map((h) => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11.5, color: "#777777" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {intel.assessments.map((a) => (
                <tr key={a.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontFamily: "monospace" }}>{a.id}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontFamily: "monospace" }}>{a.job_id}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13, fontWeight: 600 }}>{a.pii_detected}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13 }}>{a.residual_leakage}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontWeight: 600 }}>
                    {a.canary_status} ({a.canary_leaks}/{a.canary_planted})
                  </td>
                  <td style={{ padding: "11px 16px", fontSize: 13 }}>{a.qi_risk_score}% ({a.reid_risk_level})</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontWeight: 600 }}>
                    {a.release_eligible ? "YES" : "NO"}
                  </td>
                  <td style={{ padding: "11px 16px", textAlign: "right" }}>
                    <button
                      disabled={downloadingId === a.id}
                      onClick={async () => {
                        setDownloadingId(a.id);
                        setError("");
                        try {
                          await api.downloadPdf(api.downloadAssessmentPdfUrl(a.id), `MediLocker_Privacy_Intelligence_${a.id}.pdf`);
                        } catch (e: unknown) {
                          setError(e instanceof Error ? e.message : String(e));
                        }
                        setDownloadingId(null);
                      }}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 5,
                        padding: "5px 10px",
                        background: "#050505",
                        color: "#FFFFFF",
                        border: "none",
                        borderRadius: 5,
                        fontSize: 11.5,
                        fontWeight: 600,
                        cursor: downloadingId === a.id ? "wait" : "pointer",
                      }}
                    >
                      <Download size={12} />
                      {downloadingId === a.id ? "Generating…" : "Export Assessment PDF"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: "40px 20px", textAlign: "center", fontSize: 13, color: "#777777" }}>
            No privacy assessments recorded yet. Upload and process a dataset first.
          </div>
        )}
      </div>
    </div>
  );
}

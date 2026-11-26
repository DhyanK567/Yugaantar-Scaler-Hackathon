"use client";
import { useEffect, useState } from "react";
import { api, type ClinicalReport } from "@/lib/api";
import { HeartPulse, CheckCircle2, AlertTriangle } from "lucide-react";

export default function ClinicalIntegrityPage() {
  const [reports, setReports] = useState<ClinicalReport[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.clinicalReports().then(setReports).catch((e) => setError(e.message));
  }, []);

  const totalExpected = reports.reduce((s, r) => s + r.expected_values, 0);
  const totalPreserved = reports.reduce((s, r) => s + r.preserved_values, 0);
  const totalMissing = reports.reduce((s, r) => s + r.missing_values, 0);
  const totalModified = reports.reduce((s, r) => s + r.modified_values, 0);
  const latest = reports[0] ?? null;

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Clinical Integrity
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Exact numerator/denominator verification of clinical values, dosages, labs, and FHIR R4 resources.
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

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(210px, 1fr))", gap: 16, marginBottom: 28 }}>
        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "20px 22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>Preserved / Expected</span>
            <HeartPulse size={16} color="#050505" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "#050505", letterSpacing: "-1px" }}>
            {reports.length > 0 ? `${totalPreserved}/${totalExpected}` : "Not measured"}
          </div>
          <div style={{ fontSize: 11.5, color: "#666666", marginTop: 4 }}>
            {totalExpected > 0 ? `${((totalPreserved / totalExpected) * 100).toFixed(2)}% exact preservation` : "No clinical items measured"}
          </div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "20px 22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>Modified / Missing</span>
            <AlertTriangle size={16} color="#050505" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: totalMissing > 0 ? "#CC3333" : "#050505" }}>
            {reports.length > 0 ? `${totalModified} / ${totalMissing}` : "Not measured"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>Exact count across {reports.length} report(s)</div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "20px 22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>FHIR R4 Integrity</span>
            <CheckCircle2 size={16} color="#050505" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 700, color: "#050505" }}>
            {latest ? latest.fhir_integrity : "NOT_MEASURED"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>HL7 FHIR R4 Bundle validation</div>
        </div>
      </div>

      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Clinical Validation Reports ({reports.length})
        </div>
        {reports.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Report ID", "Job ID", "Preserved / Expected", "Modified", "Missing", "FHIR R4", "Created"].map((h) => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11.5, color: "#777777" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontFamily: "monospace" }}>{r.id}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontFamily: "monospace" }}>{r.job_id}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13, fontWeight: 600 }}>
                    {r.preserved_values} / {r.expected_values}
                  </td>
                  <td style={{ padding: "11px 16px", fontSize: 13 }}>{r.modified_values}</td>
                  <td style={{ padding: "11px 16px", fontSize: 13 }}>{r.missing_values}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, fontWeight: 600 }}>{r.fhir_integrity}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, color: "#777777" }}>
                    {new Date(r.created_at * 1000).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: "40px 20px", textAlign: "center", fontSize: 13, color: "#777777" }}>
            No clinical integrity reports recorded yet.
          </div>
        )}
      </div>
    </div>
  );
}

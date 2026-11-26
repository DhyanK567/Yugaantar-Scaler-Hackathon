"use client";
import { useEffect, useState } from "react";
import { api, type DashboardData } from "@/lib/api";
import { HeartPulse, CheckCircle2, AlertTriangle } from "lucide-react";

const CLINICAL_GUARANTEES = [
  {
    field: "Lab Values & Reference Ranges",
    status: "Preserved",
    detail: "Numeric measurements, units (mg/dL, mmol/L, U/L) and flags remain intact.",
  },
  {
    field: "Clinical Coding (ICD-10 / SNOMED / LOINC)",
    status: "Preserved",
    detail: "Standardised medical codes are whitelisted from PII redaction.",
  },
  {
    field: "FHIR R4 Resource Structure",
    status: "Validated",
    detail: "Patient, Observation, Condition and DiagnosticReport schemas remain compliant.",
  },
  {
    field: "Medication Dosages & Frequencies",
    status: "Preserved",
    detail: "Dosage quantities, routes and schedules are retained for research utility.",
  },
];

export default function ClinicalIntegrityPage() {
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .dashboard()
      .then(setDash)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Clinical Integrity
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Verification that clinical utility is preserved while patient identifiers are removed.
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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
          gap: 16,
          marginBottom: 28,
        }}
      >
        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "20px 22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>Clinical Values Preserved</span>
            <HeartPulse size={16} color="#050505" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#050505", letterSpacing: "-1px" }}>
            {dash?.clinical_preserved ?? "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#2D7A2D", marginTop: 4 }}>
            Verified across sanitised records
          </div>
        </div>

        <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, padding: "20px 22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <span style={{ fontSize: 12.5, color: "#777777", fontWeight: 500 }}>Total Records Checked</span>
            <CheckCircle2 size={16} color="#050505" />
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, color: "#050505", letterSpacing: "-1px" }}>
            {dash?.total_records ?? "—"}
          </div>
          <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>
            {dash ? `${dash.sanitised_files ?? 0} sanitised files` : "Awaiting backend"}
          </div>
        </div>
      </div>

      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Clinical Preservation Guarantees
        </div>
        {CLINICAL_GUARANTEES.map((item) => (
          <div
            key={item.field}
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid #EEEEEE",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>{item.field}</div>
              <div style={{ fontSize: 12.5, color: "#666666", marginTop: 3 }}>{item.detail}</div>
            </div>
            <span
              style={{
                padding: "3px 10px",
                background: "#050505",
                color: "#FFFFFF",
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                flexShrink: 0,
              }}
            >
              {item.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

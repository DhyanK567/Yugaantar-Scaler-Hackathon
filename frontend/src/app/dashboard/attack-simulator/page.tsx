"use client";
import { useEffect, useState } from "react";
import { api, type ThreatLabData } from "@/lib/api";
import { Swords, ShieldCheck, ShieldAlert, AlertTriangle, RefreshCw } from "lucide-react";

export default function AttackSimulatorPage() {
  const [data, setData] = useState<ThreatLabData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    api
      .threatLab()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
            Attack Simulator
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Adversarial linkage, singling-out, inference and canary-recall tests against sanitised output.
          </p>
        </div>
        <button
          onClick={load}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            padding: "8px 14px",
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 7,
            fontSize: 13,
            fontWeight: 500,
            color: "#050505",
            cursor: "pointer",
          }}
        >
          <RefreshCw size={13} />
          Re-evaluate
        </button>
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

      {/* Risk score card */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          padding: 24,
          marginBottom: 24,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 44,
              height: 44,
              background: "#F2F2F2",
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Swords size={20} color="#050505" />
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Residual Risk Score</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#050505", letterSpacing: "-1px" }}>
              {data?.risk_score != null ? data.risk_score : "—"}
            </div>
          </div>
        </div>
        <div style={{ fontSize: 13, color: "#555555" }}>
          {data?.attack_simulations
            ? `${data.attack_simulations.filter((a) => !a.success).length} / ${data.attack_simulations.length} attacks blocked`
            : "Awaiting simulation telemetry"}
        </div>
      </div>

      {/* Attack results */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          overflow: "hidden",
          marginBottom: 24,
        }}
      >
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Simulated Attack Vectors
        </div>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#777777" }}>
            Loading threat lab telemetry…
          </div>
        ) : data?.attack_simulations && data.attack_simulations.length > 0 ? (
          <div>
            {data.attack_simulations.map((atk, idx) => (
              <div
                key={idx}
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid #EEEEEE",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 16,
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  {atk.success ? (
                    <ShieldAlert size={18} color="#CC3333" style={{ marginTop: 2 }} />
                  ) : (
                    <ShieldCheck size={18} color="#2D7A2D" style={{ marginTop: 2 }} />
                  )}
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
                      {atk.attack_type}
                    </div>
                    <div style={{ fontSize: 12.5, color: "#666666", marginTop: 3 }}>
                      Mitigation: {atk.mitigation}
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <span
                    style={{
                      display: "inline-block",
                      padding: "3px 8px",
                      borderRadius: 4,
                      fontSize: 10.5,
                      fontWeight: 600,
                      textTransform: "uppercase",
                      background: atk.success ? "#FFE5E5" : "#050505",
                      color: atk.success ? "#CC3333" : "#FFFFFF",
                    }}
                  >
                    {atk.success ? "EXPOSED" : "BLOCKED"}
                  </span>
                  <div style={{ fontSize: 11.5, color: "#777777", marginTop: 4 }}>
                    {atk.records_at_risk} records at risk
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
            No attack simulations available yet.
          </div>
        )}
      </div>

      {/* Vulnerabilities */}
      {data?.vulnerabilities && data.vulnerabilities.length > 0 && (
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            padding: 20,
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 600, color: "#050505", marginBottom: 12 }}>
            Identified Observations
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: "#555555", lineHeight: 1.7 }}>
            {data.vulnerabilities.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

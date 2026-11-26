"use client";
import { useEffect, useState } from "react";
import { api, type JobRecord, type ThreatLabData } from "@/lib/api";
import { Swords, ShieldCheck, ShieldAlert, AlertTriangle, RefreshCw, Play } from "lucide-react";

export default function AttackSimulatorPage() {
  const [data, setData] = useState<ThreatLabData | null>(null);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [selectedJob, setSelectedJob] = useState("");
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    Promise.all([api.threatLab(), api.jobs()])
      .then(([t, j]) => {
        setData(t);
        setJobs(j);
        if (j.length > 0 && !selectedJob) setSelectedJob(j[0].id);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRunAttack() {
    if (!selectedJob) return;
    setRunning(true);
    setError("");
    try {
      await api.runAttackSimulator(selectedJob, "standard-7-vector");
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    }
    setRunning(false);
  }

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24, flexWrap: "wrap", gap: 12 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
            Attack Simulator
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Executes deterministic 7-vector re-identification attacks against sanitised job outputs.
          </p>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {jobs.length > 0 && (
            <select
              value={selectedJob}
              onChange={(e) => setSelectedJob(e.target.value)}
              style={{
                padding: "8px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 13,
                background: "#FFFFFF",
              }}
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.id} ({j.status})
                </option>
              ))}
            </select>
          )}
          <button
            onClick={handleRunAttack}
            disabled={running || !selectedJob}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 14px",
              background: "#050505",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 7,
              fontSize: 13,
              fontWeight: 600,
              cursor: running || !selectedJob ? "not-allowed" : "pointer",
            }}
          >
            <Play size={13} />
            {running ? "Running…" : "Run Simulation"}
          </button>
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
            Refresh
          </button>
        </div>
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
          <div style={{ width: 44, height: 44, background: "#F2F2F2", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Swords size={20} color="#050505" />
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#777777", fontWeight: 500 }}>Residual Uniquely Distinguishable Rate</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: "#050505", letterSpacing: "-1px" }}>
              {data?.status === "MEASURED" && data.risk_score !== null ? `${data.risk_score}%` : "Not run"}
            </div>
          </div>
        </div>
        <div style={{ fontSize: 13, color: "#555555" }}>
          {data?.attack_simulations && data.attack_simulations.length > 0
            ? `${data.attack_simulations.filter((a) => !a.success).length} / ${data.attack_simulations.length} vectors blocked`
            : "No attack simulations executed yet"}
        </div>
      </div>

      {/* Attack results */}
      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Simulated Attack Vectors
        </div>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#777777" }}>
            Loading threat lab telemetry…
          </div>
        ) : data?.attack_simulations && data.attack_simulations.length > 0 ? (
          data.attack_simulations.map((atk, idx) => (
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
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>{atk.attack_type}</div>
                  <div style={{ fontSize: 12.5, color: "#666666", marginTop: 3 }}>Mitigation: {atk.mitigation}</div>
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
          ))
        ) : (
          <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#777777" }}>
            No attack simulations available yet. Process a dataset or run a simulation above.
          </div>
        )}
      </div>
    </div>
  );
}

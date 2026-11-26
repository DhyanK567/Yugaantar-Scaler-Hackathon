"use client";
import { useEffect, useState } from "react";
import { api, type AuditEvent } from "@/lib/api";
import { FileText, RefreshCw, AlertTriangle } from "lucide-react";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [error, setError] = useState("");

  function load() {
    setError("");
    api
      .auditLogs()
      .then(setEvents)
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
            Audit Trail
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Immutable governance log of sanitisation runs, policy updates and access events.
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
          Refresh
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
          <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
            Events ({events.length})
          </span>
          <FileText size={14} color="#777777" />
        </div>

        {events.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
            No audit events recorded yet.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Severity", "Event Type", "Description", "Timestamp"].map((h) => (
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
              {events.map((ev) => (
                <tr key={ev.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "12px 20px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 7px",
                        borderRadius: 4,
                        fontSize: 10.5,
                        fontWeight: 600,
                        textTransform: "uppercase",
                        background:
                          ev.severity === "high"
                            ? "#FFE5E5"
                            : ev.severity === "medium"
                            ? "#FFF5D6"
                            : "#F2F2F2",
                        color:
                          ev.severity === "high"
                            ? "#CC3333"
                            : ev.severity === "medium"
                            ? "#8A6500"
                            : "#050505",
                      }}
                    >
                      {ev.severity ?? "info"}
                    </span>
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, fontWeight: 500, color: "#050505" }}>
                    {ev.event_type}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, color: "#555555" }}>
                    {ev.description}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 12, color: "#777777", whiteSpace: "nowrap" }}>
                    {new Date(ev.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

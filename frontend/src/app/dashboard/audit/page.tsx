"use client";
import { useEffect, useState } from "react";
import { api, type AuditEvent } from "@/lib/api";
import { FileText, RefreshCw, AlertTriangle } from "lucide-react";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  function load(targetPage = page) {
    setError("");
    api
      .auditEvents(targetPage, 25)
      .then((res) => {
        setEvents(res.events);
        setTotal(res.total);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load(page);
  }, [page]);

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
            Audit Trail
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Append-only governance log. Never exposes OTPs, secrets, or raw PII.
          </p>
        </div>
        <button
          onClick={() => load(page)}
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

      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>
            Audit Events ({total})
          </span>
          <FileText size={14} color="#777777" />
        </div>

        {events.length === 0 ? (
          <div style={{ padding: 48, textAlign: "center", fontSize: 13, color: "#777777" }}>
            No audit events recorded yet.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Outcome", "Action", "Actor", "Resource", "Details", "Timestamp"].map((h) => (
                  <th key={h} style={{ padding: "10px 16px", textAlign: "left", fontSize: 11.5, fontWeight: 600, color: "#777777" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.map((ev) => (
                <tr key={ev.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "11px 16px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        padding: "2px 7px",
                        borderRadius: 4,
                        fontSize: 10.5,
                        fontWeight: 600,
                        background:
                          ev.outcome === "FAILED" || ev.outcome === "BLOCKED"
                            ? "#FFE5E5"
                            : "#F2F2F2",
                        color:
                          ev.outcome === "FAILED" || ev.outcome === "BLOCKED"
                            ? "#CC3333"
                            : "#050505",
                      }}
                    >
                      {ev.outcome}
                    </span>
                  </td>
                  <td style={{ padding: "11px 16px", fontSize: 12.5, fontWeight: 600, color: "#050505" }}>{ev.action}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12.5, color: "#555555" }}>{ev.actor_email || "system"}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12.5, color: "#555555" }}>
                    {ev.resource_type} {ev.resource_id ? `(${ev.resource_id.slice(0, 10)})` : ""}
                  </td>
                  <td style={{ padding: "11px 16px", fontSize: 12.5, color: "#666666" }}>{ev.details || "—"}</td>
                  <td style={{ padding: "11px 16px", fontSize: 12, color: "#777777", whiteSpace: "nowrap" }}>
                    {new Date(ev.timestamp * 1000).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {total > 25 && (
          <div style={{ padding: "12px 20px", borderTop: "1px solid #EEEEEE", display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5 }}>
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              style={{ padding: "5px 12px", border: "1px solid #DCDCDC", borderRadius: 5, background: "#FFFFFF", cursor: "pointer" }}
            >
              Previous
            </button>
            <span>Page {page}</span>
            <button
              disabled={page * 25 >= total}
              onClick={() => setPage((p) => p + 1)}
              style={{ padding: "5px 12px", border: "1px solid #DCDCDC", borderRadius: 5, background: "#FFFFFF", cursor: "pointer" }}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";
import { useEffect, useState } from "react";
import { api, type ResearchRequest } from "@/lib/api";
import { Plus, Check, X, AlertTriangle } from "lucide-react";

export default function ResearchNetworkPage() {
  const [requests, setRequests] = useState<ResearchRequest[]>([]);
  const [title, setTitle] = useState("");
  const [institution, setInstitution] = useState("");
  const [purpose, setPurpose] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function load() {
    api
      .researchRequests()
      .then(setRequests)
      .catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title || !institution) return;
    setSubmitting(true);
    setError("");
    try {
      await api.createResearchRequest({ title, institution, purpose });
      setTitle("");
      setInstitution("");
      setPurpose("");
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setSubmitting(false);
  }

  async function handleAction(id: string, action: "approve" | "reject") {
    try {
      if (action === "approve") await api.approveResearch(id);
      else await api.rejectResearch(id);
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Research Network
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Governed data-access requests from external research institutions.
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

      {/* New request form */}
      <form
        onSubmit={handleCreate}
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          padding: 22,
          marginBottom: 28,
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 600, color: "#050505", marginBottom: 14 }}>
          Submit Research Collaboration Request
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.5fr auto", gap: 12, alignItems: "end" }}>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#555555", marginBottom: 5 }}>
              Study Title
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Cardiology Cohort 2026"
              required
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 13.5,
                background: "#FAFAFA",
              }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#555555", marginBottom: 5 }}>
              Institution
            </label>
            <input
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              placeholder="AIIMS Research"
              required
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 13.5,
                background: "#FAFAFA",
              }}
            />
          </div>
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#555555", marginBottom: 5 }}>
              Purpose
            </label>
            <input
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Longitudinal HbA1c outcome analysis"
              style={{
                width: "100%",
                padding: "9px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 13.5,
                background: "#FAFAFA",
              }}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "10px 18px",
              background: "#050505",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 7,
              fontSize: 13.5,
              fontWeight: 600,
              cursor: submitting ? "not-allowed" : "pointer",
            }}
          >
            <Plus size={14} />
            Submit
          </button>
        </div>
      </form>

      {/* Requests list */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1.5px solid #DCDCDC",
          borderRadius: 10,
          overflow: "hidden",
        }}
      >
        <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE", fontSize: 14, fontWeight: 600, color: "#050505" }}>
          Collaboration Requests
        </div>
        {requests.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
            No research requests yet.
          </div>
        ) : (
          requests.map((r) => (
            <div
              key={r.id}
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid #EEEEEE",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 16,
              }}
            >
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>{r.title}</div>
                <div style={{ fontSize: 12.5, color: "#777777", marginTop: 2 }}>
                  {r.institution} {r.purpose ? `· ${r.purpose}` : ""}
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span
                  style={{
                    padding: "3px 8px",
                    borderRadius: 4,
                    fontSize: 10.5,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    background:
                      r.status === "approved"
                        ? "#050505"
                        : r.status === "rejected"
                        ? "#FFE5E5"
                        : "#E6E6E6",
                    color:
                      r.status === "approved"
                        ? "#FFFFFF"
                        : r.status === "rejected"
                        ? "#CC3333"
                        : "#050505",
                  }}
                >
                  {r.status}
                </span>
                {r.status === "pending" && (
                  <>
                    <button
                      onClick={() => handleAction(r.id, "approve")}
                      title="Approve"
                      style={{
                        padding: 6,
                        border: "1px solid #DCDCDC",
                        borderRadius: 6,
                        background: "#FFFFFF",
                        cursor: "pointer",
                        color: "#050505",
                      }}
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={() => handleAction(r.id, "reject")}
                      title="Reject"
                      style={{
                        padding: 6,
                        border: "1px solid #DCDCDC",
                        borderRadius: 6,
                        background: "#FFFFFF",
                        cursor: "pointer",
                        color: "#CC3333",
                      }}
                    >
                      <X size={14} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

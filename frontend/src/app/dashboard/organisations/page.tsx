"use client";
import { useEffect, useState } from "react";
import { api, type Organisation } from "@/lib/api";
import { Building2, RefreshCw, AlertTriangle } from "lucide-react";

export default function OrganisationsPage() {
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function load() {
    setLoading(true);
    setError("");
    api
      .organisations()
      .then(setOrgs)
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
            Organisations
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Authorised hospitals, diagnostic laboratories, and research institutions for your account.
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

      {loading ? (
        <div style={{ padding: 48, textAlign: "center", color: "#777777", fontSize: 13.5 }}>
          Loading organisations…
        </div>
      ) : orgs.length === 0 ? (
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            padding: "56px 24px",
            textAlign: "center",
            color: "#777777",
            fontSize: 13.5,
          }}
        >
          No authorised organisations found for your account.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
          {orgs.map((org) => (
            <div
              key={org.id}
              style={{
                background: "#FFFFFF",
                border: "1.5px solid #DCDCDC",
                borderRadius: 10,
                padding: "22px 24px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <div
                  style={{
                    width: 36,
                    height: 36,
                    background: "#F2F2F2",
                    borderRadius: 8,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <Building2 size={17} color="#050505" strokeWidth={1.5} />
                </div>
                <span
                  style={{
                    padding: "3px 8px",
                    background: org.status.toLowerCase() === "active" ? "#050505" : "#E6E6E6",
                    color: org.status.toLowerCase() === "active" ? "#FFFFFF" : "#050505",
                    borderRadius: 4,
                    fontSize: 10.5,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  {org.status}
                </span>
              </div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#050505", marginBottom: 4 }}>
                {org.name}
              </div>
              <div style={{ fontSize: 12.5, color: "#777777", marginBottom: 14 }}>
                {org.org_type} · {org.region}
              </div>
              <div
                style={{
                  borderTop: "1px solid #EEEEEE",
                  paddingTop: 12,
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 12,
                  color: "#555555",
                }}
              >
                <span>Records contributed</span>
                <strong style={{ color: "#050505" }}>
                  {org.records_contributed.toLocaleString()}
                </strong>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

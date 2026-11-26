"use client";
import { useEffect, useState } from "react";
import { api, type Passport } from "@/lib/api";
import { FileKey2, Download, ShieldCheck, AlertTriangle } from "lucide-react";

export default function PrivacyPassportsPage() {
  const [passports, setPassports] = useState<Passport[]>([]);
  const [verifyMsg, setVerifyMsg] = useState<Record<string, string>>({});
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  function load() {
    api.passports().then(setPassports).catch((e) => setError(e.message));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleVerify(id: string) {
    try {
      const res = await api.verifyPassport(id);
      setVerifyMsg((prev) => ({
        ...prev,
        [id]: res.integrity_valid
          ? `Hash verified (${res.signature_status})`
          : "Integrity mismatch!",
      }));
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Privacy Passports
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Hash-verified compliance manifests for sanitised datasets. Unsigned manifests are explicitly labelled UNSIGNED.
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

      {passports.length === 0 ? (
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
          No Privacy Passports issued yet. Upload and process a dataset to generate a verifiable passport.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(330px, 1fr))", gap: 16 }}>
          {passports.map((p) => (
            <div
              key={p.id}
              style={{
                background: "#FFFFFF",
                border: "1.5px solid #DCDCDC",
                borderRadius: 10,
                padding: 22,
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileKey2 size={18} color="#050505" />
                  <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>{p.id}</span>
                </div>
                <span
                  style={{
                    fontSize: 10.5,
                    fontWeight: 700,
                    padding: "3px 8px",
                    borderRadius: 4,
                    background: p.signature_status === "UNSIGNED" ? "#FFF5D6" : "#050505",
                    color: p.signature_status === "UNSIGNED" ? "#8A6500" : "#FFFFFF",
                  }}
                >
                  {p.signature_status}
                </span>
              </div>

              <div style={{ fontSize: 12.5, color: "#555555", lineHeight: 1.6 }}>
                <div><strong>Dataset:</strong> {p.dataset_name || p.dataset_id || "—"}</div>
                <div><strong>Organisation:</strong> {p.organisation_name || p.organisation_id || "—"}</div>
                <div><strong>Job:</strong> <code>{p.job_id}</code></div>
                <div><strong>SHA-256:</strong> <code>{p.manifest_hash.slice(0, 20)}…</code></div>
                <div><strong>Issued:</strong> {new Date(p.created_at * 1000).toLocaleString()}</div>
              </div>

              {verifyMsg[p.id] && (
                <div style={{ fontSize: 12, fontWeight: 600, color: "#2D7A2D", background: "#F2F8F2", padding: "6px 10px", borderRadius: 5 }}>
                  {verifyMsg[p.id]}
                </div>
              )}

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
                <button
                  onClick={() => handleVerify(p.id)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "7px 12px",
                    background: "#050505",
                    color: "#FFFFFF",
                    border: "none",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  <ShieldCheck size={13} />
                  Verify Hash
                </button>
                <a
                  href={api.downloadPassportUrl(p.id, "json")}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "7px 12px",
                    background: "#F2F2F2",
                    border: "1px solid #DCDCDC",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#050505",
                    textDecoration: "none",
                    fontWeight: 500,
                  }}
                >
                  <Download size={13} />
                  JSON
                </a>
                <a
                  href={api.downloadPassportUrl(p.id, "html")}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "7px 12px",
                    background: "#F2F2F2",
                    border: "1px solid #DCDCDC",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#050505",
                    textDecoration: "none",
                    fontWeight: 500,
                  }}
                >
                  <Download size={13} />
                  HTML
                </a>
                <button
                  disabled={downloadingId === p.id}
                  onClick={async () => {
                    setDownloadingId(p.id);
                    setError("");
                    try {
                      await api.downloadPdf(api.downloadPassportUrl(p.id, "pdf"), `MediLocker_Privacy_Passport_${p.id}.pdf`);
                    } catch (e: unknown) {
                      setError(e instanceof Error ? e.message : String(e));
                    }
                    setDownloadingId(null);
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "7px 12px",
                    background: "#050505",
                    border: "none",
                    borderRadius: 6,
                    fontSize: 12,
                    color: "#FFFFFF",
                    fontWeight: 600,
                    cursor: downloadingId === p.id ? "wait" : "pointer",
                  }}
                >
                  <Download size={13} />
                  {downloadingId === p.id ? "Generating…" : "Download PDF"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

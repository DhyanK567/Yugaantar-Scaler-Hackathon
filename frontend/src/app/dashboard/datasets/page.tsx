"use client";
import { useEffect, useRef, useState } from "react";
import { api, type Dataset, type JobRecord, type Organisation } from "@/lib/api";
import {
  Upload,
  Download,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Trash2,
} from "lucide-react";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [selectedOrg, setSelectedOrg] = useState("");
  const [activeJob, setActiveJob] = useState<JobRecord | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function loadAll() {
    api.datasets().then(setDatasets).catch((e) => setError(e.message));
    api
      .organisations()
      .then((list) => {
        setOrgs(list);
        if (list.length > 0 && !selectedOrg) setSelectedOrg(list[0].id);
      })
      .catch(() => {});
  }

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    if (!activeJob) return;
    const terminal = ["COMPLETED", "COMPLETED_WITH_WARNINGS", "QUARANTINED", "BLOCKED", "FAILED", "CANCELLED"];
    if (terminal.includes(activeJob.status)) return;

    const timer = setInterval(async () => {
      try {
        const updated = await api.getJob(activeJob.id);
        setActiveJob(updated);
        if (terminal.includes(updated.status)) {
          clearInterval(timer);
          loadAll();
        }
      } catch {
        clearInterval(timer);
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [activeJob]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setError("");
    try {
      const fd = new FormData();
      if (selectedOrg) fd.append("organisation_id", selectedOrg);
      fd.append("auto_process", "true");
      for (const f of Array.from(files)) fd.append("files", f);
      const res = await api.uploadDataset(fd);
      if (res.job) setActiveJob(res.job);
      loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteDataset(id);
      loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
            Datasets
          </h1>
          <p style={{ fontSize: 13.5, color: "#777777" }}>
            Upload synthetic healthcare datasets to initiate the deterministic privacy pipeline.
          </p>
        </div>

        {orgs.length > 0 && (
          <div>
            <label style={{ display: "block", fontSize: 11, color: "#777777", marginBottom: 4 }}>
              Target Organisation
            </label>
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              style={{
                padding: "8px 12px",
                border: "1.5px solid #DCDCDC",
                borderRadius: 7,
                fontSize: 13,
                background: "#FFFFFF",
                color: "#050505",
              }}
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Upload zone */}
      <div
        style={{
          border: "2px dashed #DCDCDC",
          borderRadius: 10,
          padding: "36px 24px",
          textAlign: "center",
          background: "#FFFFFF",
          marginBottom: 24,
          cursor: "pointer",
        }}
        onClick={() => fileRef.current?.click()}
      >
        <div
          style={{
            width: 44,
            height: 44,
            background: "#F2F2F2",
            borderRadius: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 14px",
          }}
        >
          <Upload size={20} color="#050505" />
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#050505", marginBottom: 5 }}>
          {uploading ? "Uploading & Validating…" : "Click to upload dataset files"}
        </div>
        <div style={{ fontSize: 13, color: "#777777" }}>
          Supported: CSV, TSV, JSON, JSONL, TXT, PDF, PNG (Quarantine test). Raw records are never exposed in previews.
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".csv,.tsv,.json,.txt,.jsonl,.pdf,.png"
          onChange={handleUpload}
          style={{ display: "none" }}
        />
      </div>

      {error && (
        <div
          style={{
            padding: "12px 16px",
            background: "#FFF5F5",
            border: "1px solid #FFD5D5",
            borderRadius: 8,
            fontSize: 13,
            color: "#CC3333",
            marginBottom: 20,
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <AlertTriangle size={15} />
          {error}
        </div>
      )}

      {/* Live active job */}
      {activeJob && (
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #050505",
            borderRadius: 10,
            padding: "16px 20px",
            marginBottom: 24,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            {["COMPLETED", "COMPLETED_WITH_WARNINGS", "QUARANTINED", "BLOCKED", "FAILED"].includes(activeJob.status) ? (
              <CheckCircle2 size={18} color="#050505" />
            ) : (
              <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
            )}
            <div>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: "#050505" }}>
                Job {activeJob.id} — Stage: {activeJob.current_stage || activeJob.status}
              </div>
              <div style={{ fontSize: 12, color: "#666666" }}>
                Status: {activeJob.status} · Release Decision: {activeJob.release_decision || "PENDING"}
              </div>
            </div>
          </div>
          {["COMPLETED", "COMPLETED_WITH_WARNINGS"].includes(activeJob.status) && (
            <a
              href={api.downloadJobUrl(activeJob.id)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "7px 14px",
                background: "#050505",
                color: "#FFFFFF",
                borderRadius: 6,
                textDecoration: "none",
                fontSize: 12.5,
                fontWeight: 600,
              }}
            >
              <Download size={13} />
              Download Bundle
            </a>
          )}
        </div>
      )}

      {/* Datasets table */}
      <div style={{ background: "#FFFFFF", border: "1.5px solid #DCDCDC", borderRadius: 10, overflow: "hidden" }}>
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
            Registered Datasets ({datasets.length})
          </span>
          <button
            onClick={loadAll}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 5,
              fontSize: 12.5,
              color: "#777777",
              background: "none",
              border: "none",
              cursor: "pointer",
            }}
          >
            <RefreshCw size={13} />
            Refresh
          </button>
        </div>

        {datasets.length === 0 ? (
          <div style={{ padding: "48px 20px", textAlign: "center", fontSize: 13, color: "#777777" }}>
            No datasets uploaded yet. Upload files above to create a dataset and start processing.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Name", "Organisation", "Format", "Files", "Latest Job", "Created", ""].map((h) => (
                  <th key={h} style={{ padding: "10px 18px", textAlign: "left", fontSize: 11.5, color: "#777777" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "12px 18px", fontSize: 13.5, fontWeight: 500, color: "#050505" }}>
                    {d.name}
                  </td>
                  <td style={{ padding: "12px 18px", fontSize: 12.5, color: "#555555" }}>
                    {d.organisation_name || d.organisation_id}
                  </td>
                  <td style={{ padding: "12px 18px", fontSize: 12.5, color: "#777777" }}>
                    {d.format}
                  </td>
                  <td style={{ padding: "12px 18px", fontSize: 13, color: "#050505" }}>
                    {d.file_count}
                  </td>
                  <td style={{ padding: "12px 18px", fontSize: 12, fontWeight: 600, color: "#050505" }}>
                    {d.latest_job_status || "NOT_RUN"}
                  </td>
                  <td style={{ padding: "12px 18px", fontSize: 12, color: "#777777" }}>
                    {new Date(d.created_at * 1000).toLocaleDateString()}
                  </td>
                  <td style={{ padding: "12px 18px", textAlign: "right" }}>
                    <button
                      onClick={() => handleDelete(d.id)}
                      title="Delete dataset"
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#777777" }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

"use client";
import { useEffect, useRef, useState } from "react";
import { api, type Dataset, type JobRecord } from "@/lib/api";
import {
  Upload,
  FileText,
  Download,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; color: string }> = {
    done: { bg: "#050505", color: "#FFFFFF" },
    running: { bg: "#E6E6E6", color: "#050505" },
    failed: { bg: "#FFE5E5", color: "#CC3333" },
    pending: { bg: "#F2F2F2", color: "#777777" },
  };
  const s = styles[status] ?? styles.pending;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "3px 8px",
        background: s.bg,
        color: s.color,
        borderRadius: 4,
        fontSize: 10.5,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.5px",
      }}
    >
      {status}
    </span>
  );
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [uploading, setUploading] = useState(false);
  const [polling, setPolling] = useState<string | null>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.datasets().then(setDatasets).catch(() => {});
  }, []);

  // Poll active job
  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(async () => {
      try {
        const job = await api.getJob(polling);
        setJobs((prev) =>
          prev.map((j) => (j.id === job.id ? job : j))
        );
        if (job.status === "done" || job.status === "failed") {
          setPolling(null);
          clearInterval(interval);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [polling]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    setUploading(true);
    setError("");
    try {
      const fd = new FormData();
      for (const f of Array.from(files)) fd.append("files", f);
      const job = await api.createJob(fd);
      setJobs((prev) => [job, ...prev]);
      setPolling(job.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
    setUploading(false);
    if (fileRef.current) fileRef.current.value = "";
  }

  return (
    <div style={{ padding: "32px 36px" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#050505", letterSpacing: "-0.8px", marginBottom: 4 }}>
          Datasets
        </h1>
        <p style={{ fontSize: 13.5, color: "#777777" }}>
          Upload healthcare records to run the privacy pipeline.
        </p>
      </div>

      {/* Upload zone */}
      <div
        style={{
          border: "2px dashed #DCDCDC",
          borderRadius: 10,
          padding: "40px 24px",
          textAlign: "center",
          background: "#FFFFFF",
          marginBottom: 28,
          cursor: "pointer",
          transition: "border-color 0.15s",
        }}
        onClick={() => fileRef.current?.click()}
      >
        <div
          style={{
            width: 48,
            height: 48,
            background: "#F2F2F2",
            borderRadius: 10,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px",
          }}
        >
          <Upload size={22} color="#050505" />
        </div>
        <div style={{ fontSize: 15, fontWeight: 600, color: "#050505", marginBottom: 6 }}>
          {uploading ? "Uploading…" : "Drop files or click to upload"}
        </div>
        <div style={{ fontSize: 13, color: "#777777" }}>
          Supports CSV, TSV, JSON, FHIR R4, plain text. Multiple files allowed.
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".csv,.tsv,.json,.txt,.jsonl"
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

      {/* Active jobs */}
      {jobs.length > 0 && (
        <div
          style={{
            background: "#FFFFFF",
            border: "1.5px solid #DCDCDC",
            borderRadius: 10,
            overflow: "hidden",
            marginBottom: 28,
          }}
        >
          <div style={{ padding: "14px 20px", borderBottom: "1px solid #EEEEEE" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>Processing Jobs</span>
          </div>
          {jobs.map((job) => (
            <div
              key={job.id}
              style={{
                padding: "14px 20px",
                borderBottom: "1px solid #EEEEEE",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                {job.status === "running" || polling === job.id ? (
                  <Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} />
                ) : job.status === "done" ? (
                  <CheckCircle2 size={16} color="#2D7A2D" />
                ) : (
                  <FileText size={16} color="#777777" />
                )}
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "#050505" }}>
                    Job {job.id.slice(0, 12)}…
                  </div>
                  <div style={{ fontSize: 11.5, color: "#777777" }}>
                    {job.records_processed != null && `${job.records_processed} records`}
                    {job.pii_detected != null && ` · ${job.pii_detected} PII detected`}
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <StatusBadge status={job.status} />
                {job.status === "done" && (
                  <a
                    href={api.downloadJob(job.id)}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 5,
                      fontSize: 12.5,
                      color: "#050505",
                      textDecoration: "none",
                      fontWeight: 500,
                      padding: "5px 12px",
                      border: "1.5px solid #DCDCDC",
                      borderRadius: 6,
                    }}
                  >
                    <Download size={13} />
                    Download
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Datasets table */}
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
          <span style={{ fontSize: 14, fontWeight: 600, color: "#050505" }}>All Datasets</span>
          <button
            onClick={() => api.datasets().then(setDatasets).catch(() => {})}
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
          <div style={{ padding: "48px 20px", textAlign: "center", fontSize: 13, color: "#AAAAAA" }}>
            No datasets found. Upload files above to run the privacy engine.
          </div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #EEEEEE" }}>
                {["Name", "Format", "Records", "Status", "Created"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 20px",
                      textAlign: "left",
                      fontSize: 11.5,
                      fontWeight: 600,
                      color: "#777777",
                      letterSpacing: "0.3px",
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} style={{ borderBottom: "1px solid #F5F5F5" }}>
                  <td style={{ padding: "12px 20px", fontSize: 13.5, color: "#050505", fontWeight: 500 }}>
                    {d.name}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, color: "#777777" }}>
                    {d.format.toUpperCase()}
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 13, color: "#050505" }}>
                    {d.records.toLocaleString()}
                  </td>
                  <td style={{ padding: "12px 20px" }}>
                    <StatusBadge status={d.status} />
                  </td>
                  <td style={{ padding: "12px 20px", fontSize: 12, color: "#777777" }}>
                    {new Date(d.created_at).toLocaleDateString()}
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

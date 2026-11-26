"use client";

import { useEffect, useRef, useState } from "react";
import { api, type Dataset, type JobRecord, type Organisation } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { ConfirmationDialog, EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Upload, Download, RefreshCw, CheckCircle2, Loader2, Trash2, FileText } from "lucide-react";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [orgs, setOrgs] = useState<Organisation[]>([]);
  const [selectedOrg, setSelectedOrg] = useState("");
  const [activeJob, setActiveJob] = useState<JobRecord | null>(null);
  const [uploading, setUploading] = useState(false);
  const [downloadingReportJobId, setDownloadingReportJobId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
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

  async function handleGenerateReport(jobId: string) {
    setDownloadingReportJobId(jobId);
    setError("");
    try {
      const blob = await api.downloadPrivacyReportPdf(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `MediLocker_Privacy_Integrity_Report_${jobId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDownloadingReportJobId(null);
    }
  }

  async function confirmDelete() {
    if (!deleteId) return;
    try {
      await api.deleteDataset(deleteId);
      setDeleteId(null);
      loadAll();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setDeleteId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="02 · DATASET INGESTION"
        title="Datasets"
        subtitle="Upload synthetic healthcare datasets to initiate the offline deterministic privacy pipeline."
        actions={
          orgs.length > 0 ? (
            <select
              value={selectedOrg}
              onChange={(e) => setSelectedOrg(e.target.value)}
              aria-label="Target Organisation"
              className="px-3 py-2 rounded-lg bg-white border border-[#DADADA] text-[13px] font-medium text-[#090909] focus:outline-none focus:border-[#090909]"
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          ) : undefined
        }
      />

      {error && <ErrorState message={error} />}

      {/* Minimal Upload Dropzone */}
      <div
        onClick={() => fileRef.current?.click()}
        className="bg-white border border-dashed border-[#090909]/40 hover:border-[#090909] rounded-2xl p-10 text-center cursor-pointer transition-colors"
      >
        <div className="w-12 h-12 rounded-full bg-[#F4F4F2] border border-[#E5E5E5] flex items-center justify-center mx-auto mb-4">
          <Upload size={20} className="text-[#090909]" />
        </div>
        <div className="font-serif-display text-[22px] text-[#090909] mb-1">
          {uploading ? "Uploading & Validating…" : "Upload synthetic dataset"}
        </div>
        <p className="text-[13px] text-[#666666] max-w-lg mx-auto">
          Supports CSV, TSV, JSON, JSONL, TXT, and quarantine test files (PDF, PNG). Raw patient records are never previewed in the browser.
        </p>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".csv,.tsv,.json,.txt,.jsonl,.pdf,.png"
          onChange={handleUpload}
          className="hidden"
        />
      </div>

      {/* Live Job Banner */}
      {activeJob && (
        <div className="bg-white border border-[#090909] rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3.5 min-w-0">
            {["COMPLETED", "COMPLETED_WITH_WARNINGS", "QUARANTINED", "BLOCKED", "FAILED"].includes(activeJob.status) ? (
              <CheckCircle2 size={20} className="text-[#090909] shrink-0" />
            ) : (
              <Loader2 size={20} className="text-[#090909] animate-spin shrink-0" />
            )}
            <div className="min-w-0">
              <div className="text-[13.5px] font-semibold text-[#090909] truncate">
                Job {activeJob.id} — Stage: {activeJob.current_stage || activeJob.status}
              </div>
              <div className="text-[12px] text-[#666666] mt-0.5 flex flex-wrap items-center gap-2">
                <span>Status:</span>
                <StatusBadge status={activeJob.status} />
                <span>Release:</span>
                <StatusBadge status={activeJob.release_decision || "PENDING"} />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            {["COMPLETED", "COMPLETED_WITH_WARNINGS", "BLOCKED", "QUARANTINED"].includes(activeJob.status) && (
              <button
                type="button"
                onClick={() => handleGenerateReport(activeJob.id)}
                disabled={downloadingReportJobId === activeJob.id}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-[#090909] text-[#090909] text-[13px] font-medium hover:bg-[#F4F4F2] disabled:opacity-60"
              >
                {downloadingReportJobId === activeJob.id ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <FileText size={14} />
                )}
                <span>
                  {downloadingReportJobId === activeJob.id
                    ? "Generating Report…"
                    : "Generate Privacy & Integrity Report"}
                </span>
              </button>
            )}
            {["COMPLETED", "COMPLETED_WITH_WARNINGS"].includes(activeJob.status) && (
              <a
                href={api.downloadJobUrl(activeJob.id)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222]"
              >
                <Download size={14} />
                <span>Download Bundle</span>
              </a>
            )}
          </div>
        </div>
      )}

      {/* Datasets Table */}
      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-[#090909]">
            Registered Datasets ({datasets.length})
          </h2>
          <button
            type="button"
            onClick={loadAll}
            className="inline-flex items-center gap-1.5 text-[12.5px] text-[#666666] hover:text-[#090909]"
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>

        {datasets.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No datasets registered"
              description="Upload synthetic files above to register a dataset and start the privacy pipeline."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Dataset", "Organisation", "Format", "Files", "Job Status", "Created", ""].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {datasets.map((d) => (
                  <tr key={d.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3.5 text-[13.5px] font-medium text-[#090909]">{d.name}</td>
                    <td className="px-5 py-3.5 text-[13px] text-[#666666]">{d.organisation_name || d.organisation_id}</td>
                    <td className="px-5 py-3.5 text-[12px] font-mono text-[#666666]">{d.format}</td>
                    <td className="px-5 py-3.5 text-[13px] text-[#090909]">{d.file_count}</td>
                    <td className="px-5 py-3.5">
                      <StatusBadge status={d.latest_job_status || "NOT_RUN"} />
                    </td>
                    <td className="px-5 py-3.5 text-[12px] text-[#666666] whitespace-nowrap">
                      {new Date(d.created_at * 1000).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="inline-flex items-center gap-2">
                        {d.latest_job_id && (
                          <button
                            type="button"
                            onClick={() => handleGenerateReport(d.latest_job_id!)}
                            disabled={downloadingReportJobId === d.latest_job_id}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[#DADADA] bg-white text-[12px] font-medium text-[#090909] hover:bg-[#F4F4F2] disabled:opacity-60"
                          >
                            {downloadingReportJobId === d.latest_job_id ? (
                              <Loader2 size={12} className="animate-spin" />
                            ) : (
                              <FileText size={12} />
                            )}
                            <span>Generate Privacy &amp; Integrity Report</span>
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setDeleteId(d.id)}
                          aria-label={`Delete ${d.name}`}
                          className="p-1.5 rounded-md text-[#888888] hover:text-[#7F1D1D] hover:bg-[#FDF2F2]"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <ConfirmationDialog
        open={deleteId !== null}
        title="Delete dataset?"
        description="This soft-deletes the dataset from active listings while preserving immutable audit records."
        confirmLabel="Delete Dataset"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}

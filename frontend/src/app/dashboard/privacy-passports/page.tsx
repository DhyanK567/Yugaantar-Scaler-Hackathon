"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Passport, type QuarantineItem, type QuarantineSummary } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { FileKey2, Download, ShieldCheck, ShieldAlert, Lock, RefreshCw } from "lucide-react";

export default function PrivacyPassportsPage() {
  const [passports, setPassports] = useState<Passport[]>([]);
  const [quarantine, setQuarantine] = useState<QuarantineSummary | null>(null);
  const [selectedQuarantine, setSelectedQuarantine] = useState<QuarantineItem | null>(null);
  const [verifyMsg, setVerifyMsg] = useState<Record<string, string>>({});
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [pList, qData] = await Promise.all([api.passports(), api.quarantine()]);
      setPassports(pList);
      setQuarantine(qData);
      if (qData.items.length > 0 && !selectedQuarantine) {
        setSelectedQuarantine(qData.items[0]);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [selectedQuarantine]);

  useEffect(() => {
    const id = setTimeout(() => {
      void load();
    }, 0);
    return () => clearTimeout(id);
  }, [load]);

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
    <div className="space-y-8">
      <PageHeader
        eyebrow="09 · VERIFIABLE MANIFESTS & QUARANTINE"
        title="Privacy Passports & Quarantine Transparency"
        subtitle="Hash-verified compliance manifests for sanitised datasets and safe, PII-free isolation metadata for quarantined files."
      />

      {error && <ErrorState message={error} />}

      {/* Privacy Passports Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-[16px] font-semibold text-[#090909]">
            Issued Privacy Passports ({passports.length})
          </h2>
          <button
            type="button"
            onClick={() => load()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[#DADADA] bg-white text-[12px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
          >
            <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>
        </div>

        {passports.length === 0 ? (
          <EmptyState
            title="No Privacy Passports issued"
            description="Upload and process a dataset to generate a verifiable Privacy Passport."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {passports.map((p) => (
              <div
                key={p.id}
                className="bg-white border border-[#DADADA] rounded-2xl p-6 flex flex-col justify-between gap-4"
              >
                <div>
                  <div className="flex items-center justify-between gap-3 pb-4 border-b border-[#E5E5E5]">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileKey2 size={17} className="text-[#090909] shrink-0" />
                      <span className="font-mono text-[13px] font-semibold text-[#090909] truncate">
                        {p.id}
                      </span>
                    </div>
                    <StatusBadge status={p.signature_status === "UNSIGNED" ? "WARNING" : "PASS"} />
                  </div>

                  <div className="mt-4 space-y-1.5 text-[12.5px] text-[#666666]">
                    <div>
                      <span className="text-[#090909] font-medium">Dataset:</span>{" "}
                      {p.dataset_name || p.dataset_id || "—"}
                    </div>
                    <div>
                      <span className="text-[#090909] font-medium">Organisation:</span>{" "}
                      {p.organisation_name || p.organisation_id || "—"}
                    </div>
                    <div>
                      <span className="text-[#090909] font-medium">Job:</span>{" "}
                      <code className="text-[11.5px]">{p.job_id}</code>
                    </div>
                    <div>
                      <span className="text-[#090909] font-medium">SHA-256:</span>{" "}
                      <code className="text-[11.5px]">{p.manifest_hash.slice(0, 22)}…</code>
                    </div>
                    <div>
                      <span className="text-[#090909] font-medium">Issued:</span>{" "}
                      {new Date(p.created_at * 1000).toLocaleString()}
                    </div>
                  </div>

                  {verifyMsg[p.id] && (
                    <div className="mt-3 px-3 py-2 rounded-lg bg-[#ECF3EC] border border-[#C6DBC7] text-[12px] font-medium text-[#1E4620]">
                      {verifyMsg[p.id]}
                    </div>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 pt-3 border-t border-[#E5E5E5]">
                  <button
                    type="button"
                    onClick={() => handleVerify(p.id)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-[#090909] text-white text-[12px] font-medium hover:bg-[#222222]"
                  >
                    <ShieldCheck size={13} />
                    <span>Verify Hash</span>
                  </button>
                  <a
                    href={api.downloadPassportUrl(p.id, "json")}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-[#DADADA] text-[12px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
                  >
                    <Download size={13} />
                    <span>JSON</span>
                  </a>
                  <a
                    href={api.downloadPassportUrl(p.id, "html")}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-[#DADADA] text-[12px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
                  >
                    <Download size={13} />
                    <span>HTML</span>
                  </a>
                  <button
                    disabled={downloadingId === p.id}
                    onClick={async () => {
                      setDownloadingId(p.id);
                      setError("");
                      try {
                        await api.downloadPdf(
                          api.downloadPassportUrl(p.id, "pdf"),
                          `MediLocker_Privacy_Passport_${p.id}.pdf`
                        );
                      } catch (e: unknown) {
                        setError(e instanceof Error ? e.message : String(e));
                      }
                      setDownloadingId(null);
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-[#050505] text-white text-[12px] font-semibold hover:bg-[#222222] disabled:opacity-50"
                  >
                    <Download size={13} />
                    <span>{downloadingId === p.id ? "Generating…" : "Download PDF"}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Quarantined Files Transparency Section */}
      <section className="space-y-4">
        <div className="bg-white border border-[#DADADA] rounded-2xl p-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#E5E5E5] pb-4">
            <div className="flex items-center gap-2.5">
              <ShieldAlert size={18} className="text-[#090909]" />
              <div>
                <h2 className="text-[16px] font-semibold text-[#090909]">
                  Quarantined Files ({quarantine?.total_quarantined ?? 0})
                </h2>
                <p className="text-[12px] text-[#666666]">
                  Safe, PII-free isolation metadata. Raw contents, unredacted filenames, and canary strings are strictly withheld.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-[12px]">
              <span className="px-2.5 py-1 rounded-md bg-[#F4F4F2] border border-[#E5E5E5] text-[#090909]">
                Jobs Affected: {quarantine?.jobs_with_quarantine ?? 0}
              </span>
              <span className="px-2.5 py-1 rounded-md bg-[#F4F4F2] border border-[#E5E5E5] text-[#090909]">
                Pending Review: {quarantine?.pending_review_count ?? 0}
              </span>
            </div>
          </div>

          {!quarantine || quarantine.items.length === 0 ? (
            <EmptyState
              title="No quarantined files recorded"
              description="All processed dataset files passed format and privacy gate checks without quarantine isolation."
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2 overflow-x-auto border border-[#E5E5E5] rounded-xl">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                      {["Opaque Ref", "Type", "Stage Failed", "Error Code", "Status"].map((h) => (
                        <th key={h} className="px-4 py-2.5 text-[11px] font-semibold uppercase text-[#666666]">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E5E5]">
                    {quarantine.items.map((item) => {
                      const active = selectedQuarantine?.quarantine_id === item.quarantine_id;
                      return (
                        <tr
                          key={item.quarantine_id}
                          onClick={() => setSelectedQuarantine(item)}
                          className={`cursor-pointer transition-colors ${
                            active ? "bg-[#F4F4F2]" : "hover:bg-[#F9F9F8]"
                          }`}
                        >
                          <td className="px-4 py-2.5 font-mono text-[12px] font-semibold text-[#090909]">
                            {item.opaque_ref}
                          </td>
                          <td className="px-4 py-2.5 text-[12px] uppercase text-[#444444]">
                            {item.file_type}
                          </td>
                          <td className="px-4 py-2.5 text-[12px] text-[#444444]">
                            {item.stage_failed}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-[11.5px] text-[#666666]">
                            {item.error_code}
                          </td>
                          <td className="px-4 py-2.5">
                            <StatusBadge status="WARNING" />
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Safe Quarantine Detail Inspector */}
              <div className="border border-[#DADADA] rounded-xl p-4 bg-[#F9F9F8] space-y-3">
                <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-2">
                  <span className="text-[12px] font-semibold uppercase tracking-[0.06em] text-[#090909]">
                    Quarantine Detail
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-[#666666]">
                    <Lock size={11} />
                    Raw Download Blocked
                  </span>
                </div>
                {selectedQuarantine ? (
                  <div className="space-y-2 text-[12.5px] text-[#444444]">
                    <div>
                      <span className="font-semibold text-[#090909]">Opaque Ref:</span>{" "}
                      <code className="text-[11.5px]">{selectedQuarantine.opaque_ref}</code>
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Job ID:</span>{" "}
                      <code className="text-[11.5px]">{selectedQuarantine.job_id}</code>
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Dataset:</span>{" "}
                      {selectedQuarantine.dataset_name || "—"}
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">File Type / Size:</span>{" "}
                      {selectedQuarantine.file_type.toUpperCase()} ·{" "}
                      {selectedQuarantine.size_bytes != null ? `${selectedQuarantine.size_bytes} B` : "Unknown"}
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Stage Failed:</span>{" "}
                      {selectedQuarantine.stage_failed}
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Why Quarantined:</span>{" "}
                      {selectedQuarantine.reason}
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Retry Safe:</span>{" "}
                      {selectedQuarantine.retry_safe ? "Yes (after fixing input format)" : "No (requires review)"}
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Next Action:</span>{" "}
                      {selectedQuarantine.recommended_action}
                    </div>
                    <div>
                      <span className="font-semibold text-[#090909]">Manual Review:</span>{" "}
                      {selectedQuarantine.requires_manual_review ? "Required" : "Not Required"}
                    </div>
                  </div>
                ) : (
                  <div className="text-[12.5px] text-[#666666]">Select a quarantined entry to inspect safe metadata.</div>
                )}
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

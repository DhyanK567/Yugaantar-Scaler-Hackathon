"use client";

import { useEffect, useState } from "react";
import { api, type Passport } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { FileKey2, Download, ShieldCheck } from "lucide-react";

export default function PrivacyPassportsPage() {
  const [passports, setPassports] = useState<Passport[]>([]);
  const [verifyMsg, setVerifyMsg] = useState<Record<string, string>>({});
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
    <div className="space-y-6">
      <PageHeader
        eyebrow="09 · VERIFIABLE MANIFESTS"
        title="Privacy Passports"
        subtitle="Hash-verified compliance manifests for sanitised datasets. Unsigned manifests are explicitly labelled UNSIGNED."
      />

      {error && <ErrorState message={error} />}

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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

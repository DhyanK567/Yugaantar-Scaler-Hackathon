"use client";

import { useEffect, useState } from "react";
import { api, type ResearchRequest } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { Plus, Check, X } from "lucide-react";

export default function ResearchNetworkPage() {
  const [requests, setRequests] = useState<ResearchRequest[]>([]);
  const [title, setTitle] = useState("");
  const [institution, setInstitution] = useState("");
  const [purpose, setPurpose] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function load() {
    api.researchRequests().then(setRequests).catch((e) => setError(e.message));
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
    setError("");
    try {
      if (action === "approve") await api.approveResearch(id);
      else await api.rejectResearch(id);
      load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="10 · INSTITUTIONAL COLLABORATION"
        title="Research Network"
        subtitle="Governed data-access requests for sanitised research outputs. Raw patient-level data is never exposed."
      />

      {error && <ErrorState message={error} />}

      <form
        onSubmit={handleCreate}
        className="bg-white border border-[#DADADA] rounded-2xl p-6"
      >
        <h2 className="text-[15px] font-semibold text-[#090909] mb-4">
          Submit Research Collaboration Request
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-end">
          <div className="md:col-span-3">
            <label className="block text-[12px] font-medium text-[#666666] mb-1">
              Study Title
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Cardiology Cohort 2026"
              required
              className="w-full px-3 py-2 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[13.5px] focus:outline-none focus:border-[#090909]"
            />
          </div>
          <div className="md:col-span-3">
            <label className="block text-[12px] font-medium text-[#666666] mb-1">
              Institution
            </label>
            <input
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              placeholder="AIIMS Research"
              required
              className="w-full px-3 py-2 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[13.5px] focus:outline-none focus:border-[#090909]"
            />
          </div>
          <div className="md:col-span-4">
            <label className="block text-[12px] font-medium text-[#666666] mb-1">
              Purpose
            </label>
            <input
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              placeholder="Longitudinal HbA1c outcome analysis"
              className="w-full px-3 py-2 rounded-lg bg-[#F4F4F2]/60 border border-[#DADADA] text-[13.5px] focus:outline-none focus:border-[#090909]"
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222] disabled:opacity-50"
            >
              <Plus size={14} />
              <span>Submit</span>
            </button>
          </div>
        </div>
      </form>

      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#090909]">
            Collaboration Requests ({requests.length})
          </h2>
        </div>

        {requests.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No research requests yet"
              description="Submit a research collaboration request above to initiate approval governance."
            />
          </div>
        ) : (
          <div className="divide-y divide-[#E5E5E5]">
            {requests.map((r) => {
              const st = r.status.toUpperCase();
              return (
                <div
                  key={r.id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                >
                  <div>
                    <div className="text-[14px] font-semibold text-[#090909]">{r.title}</div>
                    <div className="text-[12.5px] text-[#666666] mt-0.5">
                      {r.requestor_org} {r.purpose ? `· ${r.purpose}` : ""}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <StatusBadge status={st} />
                    {(st === "SUBMITTED" || st === "PENDING" || st === "UNDER_REVIEW") && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleAction(r.id, "approve")}
                          aria-label="Approve request"
                          className="p-1.5 rounded-lg border border-[#DADADA] bg-white hover:bg-[#F4F4F2] text-[#090909]"
                        >
                          <Check size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleAction(r.id, "reject")}
                          aria-label="Reject request"
                          className="p-1.5 rounded-lg border border-[#DADADA] bg-white hover:bg-[#FDF2F2] text-[#7F1D1D]"
                        >
                          <X size={14} />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

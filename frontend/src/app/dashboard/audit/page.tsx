"use client";

import { useEffect, useState } from "react";
import { api, type AuditEvent } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState, ErrorState } from "@/components/ui/StatePanels";
import { StatusBadge } from "@/components/dashboard/StatusBadge";
import { AuditActivityChart } from "@/components/charts/AuditActivityChart";
import { RefreshCw } from "lucide-react";

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
    const id = setTimeout(() => {
      load(page);
    }, 0);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="11 · IMMUTABLE LEDGER"
        title="Audit Trail"
        subtitle="Append-only governance log. Never exposes OTPs, secrets, or raw patient identifiers."
        actions={
          <button
            type="button"
            onClick={() => load(page)}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white border border-[#DADADA] text-[13px] font-medium text-[#090909] hover:bg-[#F4F4F2]"
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        }
      />

      {error && <ErrorState message={error} />}

      <AuditActivityChart events={events} />

      <div className="bg-white border border-[#DADADA] rounded-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-[#E5E5E5] flex items-center justify-between">
          <h2 className="text-[15px] font-semibold text-[#090909]">
            Audit Events ({total})
          </h2>
        </div>

        {events.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No audit events recorded"
              description="Authentication, uploads, and release decisions are logged here automatically."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E5E5E5] bg-[#F4F4F2]/60">
                  {["Outcome", "Action", "Actor", "Resource", "Details", "Timestamp"].map((h) => (
                    <th key={h} className="px-5 py-3 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E5E5E5]">
                {events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-[#F4F4F2]/40">
                    <td className="px-5 py-3"><StatusBadge status={ev.outcome} /></td>
                    <td className="px-5 py-3 text-[12.5px] font-semibold text-[#090909]">{ev.action}</td>
                    <td className="px-5 py-3 text-[12.5px] text-[#666666]">{ev.actor_email || "system"}</td>
                    <td className="px-5 py-3 text-[12.5px] text-[#666666]">
                      {ev.resource_type} {ev.resource_id ? `(${ev.resource_id.slice(0, 10)})` : ""}
                    </td>
                    <td className="px-5 py-3 text-[12.5px] text-[#666666]">{ev.details || "—"}</td>
                    <td className="px-5 py-3 text-[12px] text-[#666666] whitespace-nowrap">
                      {new Date(ev.timestamp * 1000).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {total > 25 && (
          <div className="px-6 py-3.5 border-t border-[#E5E5E5] flex items-center justify-between text-[12.5px]">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1.5 rounded-lg border border-[#DADADA] bg-white disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-[#666666]">Page {page}</span>
            <button
              type="button"
              disabled={page * 25 >= total}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 rounded-lg border border-[#DADADA] bg-white disabled:opacity-40"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

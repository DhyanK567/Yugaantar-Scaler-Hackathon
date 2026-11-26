import Link from "next/link";
import type { AuditEvent } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

interface AuditEventsPanelProps {
  events: AuditEvent[];
}

export function AuditEventsPanel({ events }: AuditEventsPanelProps) {
  return (
    <section
      aria-label="Audit Events"
      className="bg-white border border-[#E6E6E6] rounded-2xl overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.03)] min-w-0 flex flex-col"
    >
      <div className="px-5 py-4 border-b border-[#E6E6E6] flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-[#050505]">Audit Events</h2>
        <Link
          href="/dashboard/audit"
          className="text-[12.5px] font-medium text-[#050505] hover:underline shrink-0"
        >
          View All →
        </Link>
      </div>

      {events.length === 0 ? (
        <div className="p-10 text-center flex-1 flex flex-col items-center justify-center">
          <p className="text-[13.5px] font-medium text-[#050505]">
            No audit events recorded
          </p>
          <p className="text-[12.5px] text-[#666666] mt-1">
            Authentication, uploads, and release decisions are logged here automatically.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-[#F2F2F2]">
          {events.slice(0, 6).map((ev) => (
            <div
              key={ev.id}
              className="px-5 py-3 flex items-start justify-between gap-3 hover:bg-[#FAFAFA]"
            >
              <div className="min-w-0">
                <div className="text-[12.5px] font-semibold text-[#050505] truncate">
                  {ev.action}
                </div>
                <div className="text-[11.5px] text-[#666666] truncate mt-0.5">
                  {ev.actor_email || "system"} · {ev.resource_type}
                </div>
              </div>

              <div className="text-right shrink-0">
                <StatusBadge status={ev.outcome} />
                <div className="text-[10.5px] text-[#666666] mt-1 whitespace-nowrap">
                  {new Date(ev.timestamp * 1000).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

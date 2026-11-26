import type { DashboardOverview } from "@/lib/api";
import { ShieldCheck } from "lucide-react";
import { StatusBadge } from "./StatusBadge";

interface ReleaseReadinessPanelProps {
  health: DashboardOverview["privacy_health"];
}

export function ReleaseReadinessPanel({ health }: ReleaseReadinessPanelProps) {
  return (
    <section
      aria-label="Overall Release Readiness"
      className="bg-white border border-[#DADADA] rounded-2xl p-5 sm:p-6"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 items-center">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-2">
            <ShieldCheck size={14} className="text-[#090909]" />
            <span>Overall Release Readiness</span>
          </div>
          <StatusBadge status={health.overall_readiness} />
        </div>

        <div className="min-w-0">
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1">
            Latest Processing Job
          </div>
          <div className="text-[13.5px] font-medium text-[#090909] truncate">
            {health.latest_job_id
              ? `${health.latest_job_id} (${health.latest_job_status})`
              : "No jobs executed"}
          </div>
        </div>

        <div className="min-w-0">
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1">
            Critical Risks
          </div>
          <div
            className={`font-serif-display text-[26px] leading-none ${
              health.critical_unresolved_risks > 0 ? "text-[#7F1D1D]" : "text-[#090909]"
            }`}
          >
            {health.critical_unresolved_risks}
          </div>
        </div>

        <div className="min-w-0">
          <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1">
            Pending Checks
          </div>
          <div className="font-serif-display text-[26px] leading-none text-[#090909]">
            {health.pending_checks}
          </div>
        </div>
      </div>
    </section>
  );
}

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
      className="bg-white border border-[#E6E6E6] rounded-2xl p-5 sm:p-6 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 items-center">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666] mb-2">
            <ShieldCheck size={14} className="text-[#050505]" />
            <span>Overall Release Readiness</span>
          </div>
          <StatusBadge status={health.overall_readiness} />
        </div>

        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666] mb-1">
            Latest Processing Job
          </div>
          <div className="text-[13.5px] font-semibold text-[#050505] truncate">
            {health.latest_job_id
              ? `${health.latest_job_id} (${health.latest_job_status})`
              : "No jobs executed"}
          </div>
        </div>

        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666] mb-1">
            Critical Risks
          </div>
          <div
            className={`text-[18px] font-bold ${
              health.critical_unresolved_risks > 0 ? "text-[#B91C1C]" : "text-[#050505]"
            }`}
          >
            {health.critical_unresolved_risks}
          </div>
        </div>

        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-[#666666] mb-1">
            Pending Checks
          </div>
          <div className="text-[18px] font-bold text-[#050505]">
            {health.pending_checks}
          </div>
        </div>
      </div>
    </section>
  );
}

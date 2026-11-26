import { RefreshCw, Building2 } from "lucide-react";

interface DashboardHeaderProps {
  organisationName?: string;
  freshness?: number;
  refreshing: boolean;
  onRefresh: () => void;
}

export function DashboardHeader({
  organisationName,
  freshness,
  refreshing,
  onRefresh,
}: DashboardHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 pb-6 border-b border-[#E5E5E5]">
      <div className="min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
          OPERATIONAL INTELLIGENCE CENTRE
        </div>
        <h1 className="font-serif-display text-[30px] sm:text-[34px] leading-[1.1] tracking-[-0.015em] text-[#090909]">
          Privacy Dashboard
        </h1>
        <p className="text-[13.5px] text-[#666666] mt-1.5">
          Evidence-based privacy, identity continuity, and clinical integrity telemetry.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 shrink-0">
        {organisationName && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-[#DADADA] text-[12.5px] font-medium text-[#090909]">
            <Building2 size={14} className="text-[#666666]" />
            <span className="truncate max-w-[200px]">{organisationName}</span>
          </div>
        )}

        {freshness != null && (
          <span className="text-[12px] text-[#888888] whitespace-nowrap">
            Updated {new Date(freshness * 1000).toLocaleTimeString()}
          </span>
        )}

        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-white border border-[#090909] text-[12.5px] font-medium text-[#090909] hover:bg-[#090909] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
          <span>{refreshing ? "Refreshing…" : "Refresh"}</span>
        </button>
      </div>
    </div>
  );
}

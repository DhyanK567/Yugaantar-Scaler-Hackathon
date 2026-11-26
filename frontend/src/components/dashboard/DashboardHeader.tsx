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
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-[#E6E6E6]">
      <div className="min-w-0">
        <h1 className="text-[24px] sm:text-[26px] font-bold tracking-[-0.02em] text-[#050505]">
          Privacy Dashboard
        </h1>
        <p className="text-[13.5px] text-[#666666] mt-1">
          Evidence-based privacy, identity continuity, and clinical integrity telemetry.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 shrink-0">
        {organisationName && (
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-[#E6E6E6] text-[12.5px] font-medium text-[#050505]">
            <Building2 size={14} className="text-[#666666]" />
            <span className="truncate max-w-[200px]">{organisationName}</span>
          </div>
        )}

        {freshness != null && (
          <span className="text-[12px] text-[#666666] whitespace-nowrap">
            Updated {new Date(freshness * 1000).toLocaleTimeString()}
          </span>
        )}

        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-white border border-[#050505] text-[12.5px] font-medium text-[#050505] hover:bg-[#050505] hover:text-white transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
          <span>{refreshing ? "Refreshing…" : "Refresh"}</span>
        </button>
      </div>
    </div>
  );
}

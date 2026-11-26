import type { MetricStatus } from "@/lib/api";

export type WorkflowStageStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "WARNING"
  | "FAILED"
  | "BLOCKED";

const STYLES: Record<string, string> = {
  PASS: "bg-[#050505] text-white",
  APPROVED: "bg-[#050505] text-white",
  COMPLETED: "bg-[#050505] text-white",
  SUCCESS: "bg-[#050505] text-white",
  WARNING: "bg-[#FFF5D6] text-[#8A6500] border border-[#F0DC9B]",
  COMPLETED_WITH_WARNINGS: "bg-[#FFF5D6] text-[#8A6500] border border-[#F0DC9B]",
  QUARANTINED: "bg-[#FFF5D6] text-[#8A6500] border border-[#F0DC9B]",
  IN_PROGRESS: "bg-[#E6E6E6] text-[#050505]",
  PROCESSING: "bg-[#E6E6E6] text-[#050505]",
  FAILED: "bg-[#FFE5E5] text-[#B91C1C] border border-[#FECACA]",
  BLOCKED: "bg-[#FFE5E5] text-[#B91C1C] border border-[#FECACA]",
  NOT_RUN: "bg-[#F2F2F2] text-[#666666] border border-[#E6E6E6]",
  NOT_MEASURED: "bg-[#F2F2F2] text-[#666666] border border-[#E6E6E6]",
  NOT_STARTED: "bg-[#F2F2F2] text-[#666666] border border-[#E6E6E6]",
};

export function StatusBadge({
  status,
}: {
  status: MetricStatus | WorkflowStageStatus | string;
}) {
  const cls =
    STYLES[status] ?? "bg-[#F2F2F2] text-[#050505] border border-[#E6E6E6]";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10.5px] font-semibold tracking-[0.04em] uppercase whitespace-nowrap ${cls}`}
    >
      {status}
    </span>
  );
}

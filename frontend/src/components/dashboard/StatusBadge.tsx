import type { MetricStatus } from "@/lib/api";

export type WorkflowStageStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "WARNING"
  | "FAILED"
  | "BLOCKED";

const STYLES: Record<string, string> = {
  PASS: "bg-[#ECF3EC] text-[#1E4620] border border-[#C6DBC7]",
  APPROVED: "bg-[#ECF3EC] text-[#1E4620] border border-[#C6DBC7]",
  COMPLETED: "bg-[#090909] text-white border border-[#090909]",
  SUCCESS: "bg-[#ECF3EC] text-[#1E4620] border border-[#C6DBC7]",
  WARNING: "bg-[#FDF6E7] text-[#7A5200] border border-[#E8D5A7]",
  PASS_WITH_WARNINGS: "bg-[#FDF6E7] text-[#7A5200] border border-[#E8D5A7]",
  COMPLETED_WITH_WARNINGS: "bg-[#FDF6E7] text-[#7A5200] border border-[#E8D5A7]",
  QUARANTINED: "bg-[#FDF6E7] text-[#7A5200] border border-[#E8D5A7]",
  IN_PROGRESS: "bg-[#E6E6E6] text-[#090909] border border-[#DADADA]",
  RUNNING: "bg-[#E6E6E6] text-[#090909] border border-[#DADADA]",
  PROCESSING: "bg-[#E6E6E6] text-[#090909] border border-[#DADADA]",
  FAILED: "bg-[#FDF2F2] text-[#7F1D1D] border border-[#E8C5C5]",
  BLOCKED: "bg-[#FDF2F2] text-[#7F1D1D] border border-[#E8C5C5]",
  NOT_RUN: "bg-[#F4F4F2] text-[#666666] border border-[#DADADA]",
  NOT_MEASURED: "bg-[#F4F4F2] text-[#666666] border border-[#DADADA]",
  NOT_STARTED: "bg-[#F4F4F2] text-[#666666] border border-[#DADADA]",
};

export function StatusBadge({
  status,
}: {
  status: MetricStatus | WorkflowStageStatus | string;
}) {
  const cls =
    STYLES[status] ?? "bg-[#F4F4F2] text-[#090909] border border-[#DADADA]";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10.5px] font-semibold tracking-[0.04em] uppercase whitespace-nowrap ${cls}`}
    >
      {status}
    </span>
  );
}

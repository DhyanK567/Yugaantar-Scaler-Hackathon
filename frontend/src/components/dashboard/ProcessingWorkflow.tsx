import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { JobRecord } from "@/lib/api";
import { StatusBadge, type WorkflowStageStatus } from "./StatusBadge";

interface ProcessingWorkflowProps {
  latestJob?: JobRecord | null;
}

const STAGES = [
  { key: "INGESTION", title: "Dataset Ingestion", href: "/dashboard/datasets" },
  { key: "PRIVACY", title: "Privacy Detection", href: "/dashboard/privacy-intelligence" },
  { key: "IDENTITY", title: "Identity Continuity", href: "/dashboard/identity-continuity" },
  { key: "CLINICAL", title: "Clinical Validation", href: "/dashboard/clinical-integrity" },
  { key: "SECURITY", title: "Risk & Attack Assessment", href: "/dashboard/attack-simulator" },
  { key: "RELEASE", title: "Release Decision", href: "/dashboard/privacy-passports" },
];

function computeStageStatuses(job?: JobRecord | null): WorkflowStageStatus[] {
  if (!job) return STAGES.map(() => "NOT_STARTED");

  const st = (job.status || "").toUpperCase();
  const stage = (job.current_stage || st).toUpperCase();

  if (st === "COMPLETED") {
    return ["COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED", "COMPLETED"];
  }
  if (st === "COMPLETED_WITH_WARNINGS" || st === "QUARANTINED") {
    return ["COMPLETED", "COMPLETED", "COMPLETED", "WARNING", "COMPLETED", "WARNING"];
  }
  if (st === "BLOCKED") {
    return ["COMPLETED", "FAILED", "COMPLETED", "COMPLETED", "FAILED", "BLOCKED"];
  }
  if (st === "FAILED") {
    return ["FAILED", "NOT_STARTED", "NOT_STARTED", "NOT_STARTED", "NOT_STARTED", "BLOCKED"];
  }

  // Active in-flight stage mapping
  const stageIndexMap: Record<string, number> = {
    CREATED: 0,
    VALIDATING: 0,
    QUEUED: 0,
    PROCESSING: 1,
    PRIVACY_ANALYSIS: 1,
    CLINICAL_VALIDATION: 3,
    SECURITY_VALIDATION: 4,
  };
  const activeIdx = stageIndexMap[stage] ?? 0;

  return STAGES.map((_, idx) => {
    if (idx < activeIdx) return "COMPLETED";
    if (idx === activeIdx) return "IN_PROGRESS";
    return "NOT_STARTED";
  });
}

export function ProcessingWorkflow({ latestJob }: ProcessingWorkflowProps) {
  const statuses = computeStageStatuses(latestJob);

  return (
    <section
      aria-label="Processing Workflow"
      className="bg-white border border-[#E6E6E6] rounded-2xl p-5 sm:p-6 shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-5">
        <div>
          <h2 className="text-[15px] font-semibold text-[#050505]">
            Processing Workflow
          </h2>
          <p className="text-[12.5px] text-[#666666] mt-0.5">
            {latestJob
              ? `Reflecting latest job ${latestJob.id} (${latestJob.status})`
              : "No processing job has been executed yet"}
          </p>
        </div>
        <Link
          href="/dashboard/privacy-engine"
          className="text-[12.5px] font-medium text-[#050505] hover:underline shrink-0"
        >
          Inspect Engine →
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        {STAGES.map((stage, idx) => {
          const status = statuses[idx];
          const isCurrent = status === "IN_PROGRESS";
          return (
            <Link
              key={stage.key}
              href={stage.href}
              className={`relative flex flex-col justify-between p-3.5 rounded-xl border transition-colors min-w-0 ${
                isCurrent
                  ? "bg-[#F2F2F2] border-[#050505]"
                  : "bg-[#FAFAFA] border-[#E6E6E6] hover:border-[#050505]"
              }`}
            >
              <div className="flex items-center justify-between gap-1 mb-2.5">
                <span className="text-[11px] font-bold text-[#666666]">
                  0{idx + 1}
                </span>
                {idx < STAGES.length - 1 && (
                  <ChevronRight size={13} className="hidden lg:block text-[#999999]" />
                )}
              </div>
              <div className="text-[13px] font-semibold text-[#050505] leading-snug mb-3">
                {stage.title}
              </div>
              <div>
                <StatusBadge status={status} />
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}

import Link from "next/link";
import { Upload, Shield, FileKey2, ArrowRight } from "lucide-react";

interface GettingStartedPanelProps {
  hasProcessedData: boolean;
}

export function GettingStartedPanel({ hasProcessedData }: GettingStartedPanelProps) {
  if (hasProcessedData) {
    return (
      <section
        aria-label="Operational Shortcuts"
        className="bg-white border border-[#E6E6E6] rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
      >
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold text-[#050505]">
            Operational Actions
          </h2>
          <p className="text-[13px] text-[#666666] mt-0.5">
            Upload another synthetic cohort, inspect privacy passports, or review audit logs.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3 shrink-0">
          <Link
            href="/dashboard/datasets"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#050505] text-white text-[13px] font-semibold hover:bg-[#222222] transition-colors"
          >
            <Upload size={14} />
            <span>Upload Dataset</span>
          </Link>
          <Link
            href="/dashboard/privacy-passports"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-[#050505] text-[#050505] text-[13px] font-medium hover:bg-[#F2F2F2] transition-colors"
          >
            <FileKey2 size={14} />
            <span>Privacy Passports</span>
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="Getting Started"
      className="bg-white border border-[#E6E6E6] rounded-2xl p-6 sm:p-7 shadow-[0_1px_2px_rgba(0,0,0,0.03)] flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5"
    >
      <div className="min-w-0 max-w-2xl">
        <div className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[#666666] mb-2">
          <Shield size={13} className="text-[#050505]" />
          <span>First-Run Workflow</span>
        </div>
        <h2 className="text-[18px] sm:text-[20px] font-bold tracking-[-0.01em] text-[#050505]">
          Secure your first healthcare dataset
        </h2>
        <p className="text-[13.5px] text-[#666666] mt-1.5 leading-relaxed">
          Upload a synthetic healthcare dataset to run MediLocker&apos;s offline privacy protection pipeline.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3 shrink-0">
        <Link
          href="/dashboard/datasets"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#050505] text-white text-[13.5px] font-semibold hover:bg-[#222222] transition-colors"
        >
          <Upload size={15} />
          <span>Upload Dataset</span>
        </Link>
        <Link
          href="/dashboard/privacy-engine"
          className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white border border-[#050505] text-[#050505] text-[13.5px] font-medium hover:bg-[#F2F2F2] transition-colors"
        >
          <span>Explore Privacy Engine</span>
          <ArrowRight size={14} />
        </Link>
      </div>
    </section>
  );
}

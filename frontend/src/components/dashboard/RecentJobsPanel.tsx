import Link from "next/link";
import type { JobRecord } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

interface RecentJobsPanelProps {
  jobs: JobRecord[];
}

export function RecentJobsPanel({ jobs }: RecentJobsPanelProps) {
  return (
    <section
      aria-label="Recent Jobs"
      className="bg-white border border-[#E6E6E6] rounded-2xl overflow-hidden shadow-[0_1px_2px_rgba(0,0,0,0.03)] min-w-0 flex flex-col"
    >
      <div className="px-5 py-4 border-b border-[#E6E6E6] flex items-center justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-[#050505]">Recent Jobs</h2>
        <Link
          href="/dashboard/privacy-engine"
          className="text-[12.5px] font-medium text-[#050505] hover:underline shrink-0"
        >
          View All →
        </Link>
      </div>

      {jobs.length === 0 ? (
        <div className="p-10 text-center flex-1 flex flex-col items-center justify-center">
          <p className="text-[13.5px] font-medium text-[#050505]">
            No processing jobs yet
          </p>
          <p className="text-[12.5px] text-[#666666] mt-1 mb-4">
            Upload a synthetic dataset to start your first privacy run.
          </p>
          <Link
            href="/dashboard/datasets"
            className="px-4 py-2 rounded-xl bg-[#050505] text-white text-[12.5px] font-semibold hover:bg-[#222222]"
          >
            Upload Dataset
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#E6E6E6] bg-[#FAFAFA]">
                <th className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-[#666666]">
                  Job ID
                </th>
                <th className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-[#666666]">
                  Dataset
                </th>
                <th className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-[#666666]">
                  Status
                </th>
                <th className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-[#666666]">
                  Release
                </th>
                <th className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-[#666666]">
                  Created
                </th>
                <th className="px-4 py-2.5 text-[11px] font-semibold uppercase tracking-[0.04em] text-[#666666] text-right">
                  Details
                </th>
              </tr>
            </thead>
            <tbody>
              {jobs.slice(0, 6).map((job) => (
                <tr
                  key={job.id}
                  className="border-b border-[#F2F2F2] last:border-b-0 hover:bg-[#FAFAFA]"
                >
                  <td className="px-4 py-3 text-[12px] font-mono text-[#050505] whitespace-nowrap">
                    {job.id.slice(0, 14)}
                  </td>
                  <td className="px-4 py-3 text-[12.5px] text-[#050505] max-w-[160px] truncate">
                    {job.dataset_name || job.input_name || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={job.status} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={job.release_decision || "PENDING"} />
                  </td>
                  <td className="px-4 py-3 text-[11.5px] text-[#666666] whitespace-nowrap">
                    {new Date(job.created_at * 1000).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <Link
                      href="/dashboard/privacy-passports"
                      className="text-[12px] font-medium text-[#050505] hover:underline"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { MetricCardData } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";

interface MetricCardProps {
  label: string;
  metric: MetricCardData;
  href: string;
  icon: React.ElementType;
}

export function MetricCard({ label, metric, href, icon: Icon }: MetricCardProps) {
  return (
    <Link
      href={href}
      className="group bg-white border border-[#E6E6E6] rounded-2xl p-5 flex flex-col justify-between h-full min-w-0 hover:border-[#050505] transition-colors shadow-[0_1px_2px_rgba(0,0,0,0.03)]"
    >
      <div className="flex items-center justify-between gap-3 mb-4">
        <span className="text-[13px] font-medium text-[#666666] truncate">
          {label}
        </span>
        <div className="w-8 h-8 rounded-lg bg-[#F2F2F2] border border-[#E6E6E6] flex items-center justify-center shrink-0">
          <Icon size={15} strokeWidth={1.6} className="text-[#050505]" />
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 mb-3 min-w-0">
        <div className="text-[22px] sm:text-[24px] font-bold tracking-[-0.02em] text-[#050505] whitespace-nowrap truncate">
          {metric.display}
        </div>
        <StatusBadge status={metric.status} />
      </div>

      <div className="flex items-center justify-between gap-2 pt-3 border-t border-[#F2F2F2] min-w-0">
        <span className="text-[12px] text-[#666666] truncate">
          {metric.description}
        </span>
        <ArrowUpRight
          size={14}
          className="text-[#666666] group-hover:text-[#050505] shrink-0 transition-colors"
        />
      </div>
    </Link>
  );
}

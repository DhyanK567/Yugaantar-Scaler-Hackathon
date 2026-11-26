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
      className="group bg-white border border-[#DADADA] rounded-2xl p-5 sm:p-6 flex flex-col justify-between h-full min-w-0 hover:border-[#090909] transition-colors"
    >
      <div className="flex items-center justify-between gap-3 mb-4">
        <span className="text-[12.5px] font-medium text-[#666666] truncate">
          {label}
        </span>
        <div className="w-8 h-8 rounded-lg bg-[#F4F4F2] border border-[#E5E5E5] flex items-center justify-center shrink-0">
          <Icon size={15} strokeWidth={1.6} className="text-[#090909]" />
        </div>
      </div>

      <div className="flex items-baseline justify-between gap-3 mb-3 min-w-0">
        <div className="font-serif-display text-[30px] sm:text-[34px] leading-none tracking-[-0.02em] text-[#090909] whitespace-nowrap truncate">
          {metric.display}
        </div>
        <StatusBadge status={metric.status} />
      </div>

      <div className="flex items-center justify-between gap-2 pt-3 border-t border-[#E5E5E5] min-w-0">
        <span className="text-[12px] text-[#666666] truncate">
          {metric.description}
        </span>
        <ArrowUpRight
          size={14}
          className="text-[#888888] group-hover:text-[#090909] shrink-0 transition-colors"
        />
      </div>
    </Link>
  );
}

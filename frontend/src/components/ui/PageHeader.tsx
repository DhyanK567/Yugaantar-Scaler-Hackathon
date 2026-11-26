import React from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function PageHeader({ eyebrow, title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 pb-6 border-b border-[#E5E5E5]">
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#888888] mb-1.5">
            {eyebrow}
          </div>
        )}
        <h1 className="font-serif-display text-[28px] sm:text-[32px] leading-[1.15] tracking-[-0.01em] text-[#090909]">
          {title}
        </h1>
        {subtitle && (
          <p className="text-[13.5px] text-[#666666] mt-1.5 max-w-2xl leading-relaxed">
            {subtitle}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2.5 shrink-0">{actions}</div>
      )}
    </div>
  );
}

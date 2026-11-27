"use client";

import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import Sidebar from "./Sidebar";
import { api } from "@/lib/api";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [judgeMode, setJudgeMode] = useState(false);

  useEffect(() => {
    api
      .authConfig()
      .then((c) => setJudgeMode(Boolean(c.judge_mode)))
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-[#F4F4F2] text-[#090909] flex flex-col lg:flex-row">
      {/* Mobile top bar */}
      <header className="lg:hidden sticky top-0 z-30 bg-white border-b border-[#DADADA] px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <img
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            className="w-7 h-7 rounded-full object-cover"
          />
          <span className="font-serif-display text-[18px] text-[#090909]">
            MediLocker
          </span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="p-2 rounded-lg border border-[#DADADA] text-[#090909] hover:bg-[#F4F4F2]"
        >
          <Menu size={18} />
        </button>
      </header>

      <Sidebar
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
      />

      <main className="flex-1 min-w-0 w-full">
        {judgeMode && (
          <div className="bg-[#090909] text-white px-4 sm:px-6 lg:px-10 py-2 flex flex-wrap items-center justify-between gap-2 text-[12px]">
            <div className="flex items-center gap-2.5">
              <span className="px-2 py-0.5 rounded bg-white text-[#090909] font-bold tracking-[0.06em] uppercase text-[10.5px]">
                LOCAL EVALUATION MODE
              </span>
              <span className="text-[#E5E5E5]">
                Offline synthetic-data evaluation active. No login or internet connection required.
              </span>
            </div>
            <span className="text-[#A3A3A3] font-mono text-[11px]">
              MEDILOCKER_MODE=judge · CPU-only
            </span>
          </div>
        )}
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10 py-7 lg:py-9">
          {children}
        </div>
      </main>
    </div>
  );
}

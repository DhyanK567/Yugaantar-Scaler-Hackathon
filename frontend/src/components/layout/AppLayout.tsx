"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import Sidebar from "./Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

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
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10 py-7 lg:py-9">
          {children}
        </div>
      </main>
    </div>
  );
}

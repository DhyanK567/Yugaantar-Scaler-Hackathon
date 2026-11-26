"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import Sidebar from "./Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-[#F2F2F2] text-[#050505] flex flex-col lg:flex-row">
      {/* Mobile top bar */}
      <header className="lg:hidden sticky top-0 z-30 bg-white border-b border-[#E6E6E6] px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <img
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            className="w-7 h-7 rounded-full object-cover"
          />
          <span className="font-semibold text-[15px] tracking-tight text-[#050505]">
            MediLocker
          </span>
        </div>
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="p-2 rounded-lg border border-[#E6E6E6] text-[#050505] hover:bg-[#F2F2F2]"
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
        <div className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-9 py-6 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}

"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Menu, X } from "lucide-react";

const NAV_LINKS = [
  { label: "Features", href: "/#features" },
  { label: "Pricing", href: "/pricing" },
  { label: "FAQ", href: "/faq" },
];

export default function MarketingNav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-[#F4F4F2]/95 backdrop-blur-sm border-b border-[#E5E5E5]">
      <div className="max-w-[1160px] mx-auto px-6 h-16 flex items-center justify-between gap-6">
        {/* Left: Logo + Wordmark */}
        <Link href="/" className="flex items-center gap-2.5 shrink-0">
          <Image
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            width={28}
            height={28}
            className="rounded-full"
          />
          <span className="font-serif-display text-[19px] tracking-[-0.01em] text-[#090909]">
            MediLocker
          </span>
        </Link>

        {/* Centre: Links */}
        <nav className="hidden md:flex items-center gap-8" aria-label="Primary">
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-[13.5px] text-[#666666] hover:text-[#090909] transition-colors"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        {/* Right: Actions */}
        <div className="flex items-center gap-4 shrink-0">
          <Link
            href="/login"
            className="hidden sm:inline-block text-[13.5px] font-medium text-[#090909] hover:text-[#666666] transition-colors"
          >
            Sign in
          </Link>
          <Link
            href="/register"
            className="px-4 py-2 rounded-full bg-[#090909] text-white text-[13px] font-medium hover:bg-[#222222] transition-colors"
          >
            Get started
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label="Toggle menu"
            className="md:hidden p-1.5 rounded-lg border border-[#DADADA] text-[#090909]"
          >
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>
      </div>

      {open && (
        <div className="md:hidden border-t border-[#E5E5E5] bg-[#F4F4F2] px-6 py-4 space-y-3">
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="block text-[14px] text-[#090909] py-1"
            >
              {l.label}
            </Link>
          ))}
          <Link
            href="/login"
            onClick={() => setOpen(false)}
            className="block text-[14px] font-medium text-[#090909] py-1"
          >
            Sign in
          </Link>
        </div>
      )}
    </header>
  );
}

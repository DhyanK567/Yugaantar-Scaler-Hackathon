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
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 50,
        background: "#FFFFFF",
        borderBottom: "1px solid #DCDCDC",
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "0 24px",
          height: 60,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {/* Logo */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            textDecoration: "none",
          }}
        >
          <Image
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            width={30}
            height={30}
            style={{ borderRadius: "50%" }}
          />
          <span
            style={{
              fontWeight: 600,
              fontSize: 16,
              color: "#050505",
              letterSpacing: "-0.3px",
            }}
          >
            MediLocker
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav
          style={{
            display: "flex",
            alignItems: "center",
            gap: 32,
          }}
          className="hidden-mobile"
        >
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              style={{
                fontSize: 14,
                color: "#555555",
                textDecoration: "none",
                fontWeight: 400,
              }}
            >
              {l.label}
            </Link>
          ))}
        </nav>

        {/* CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Link
            href="/login"
            style={{
              fontSize: 14,
              color: "#050505",
              textDecoration: "none",
              fontWeight: 500,
            }}
          >
            Sign in
          </Link>
          <Link
            href="/register"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 18px",
              background: "#050505",
              color: "#FFFFFF",
              borderRadius: 6,
              textDecoration: "none",
              fontSize: 14,
              fontWeight: 500,
            }}
          >
            Get Started
          </Link>
          <button
            onClick={() => setOpen(!open)}
            style={{
              display: "none",
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#050505",
              padding: 4,
            }}
            aria-label="Menu"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div
          style={{
            borderTop: "1px solid #DCDCDC",
            background: "#FFFFFF",
            padding: "12px 24px 20px",
          }}
        >
          {NAV_LINKS.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              style={{
                display: "block",
                padding: "10px 0",
                fontSize: 15,
                color: "#050505",
                textDecoration: "none",
                borderBottom: "1px solid #EEEEEE",
              }}
            >
              {l.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}

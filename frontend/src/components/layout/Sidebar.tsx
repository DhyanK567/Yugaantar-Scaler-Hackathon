"use client";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Database,
  Shield,
  Brain,
  Swords,
  Users2,
  HeartPulse,
  FileKey2,
  Network,
  FileText,
  Settings,
  LogOut,
  ChevronRight,
} from "lucide-react";

const NAV = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Datasets", href: "/dashboard/datasets", icon: Database },
  { label: "Privacy Engine", href: "/dashboard/privacy-engine", icon: Shield },
  { label: "Privacy Intelligence", href: "/dashboard/privacy-intelligence", icon: Brain },
  { label: "Attack Simulator", href: "/dashboard/attack-simulator", icon: Swords },
  { label: "Organisations", href: "/dashboard/organisations", icon: Users2 },
  { label: "Identity Continuity", href: "/dashboard/identity-continuity", icon: Network },
  { label: "Clinical Integrity", href: "/dashboard/clinical-integrity", icon: HeartPulse },
  { label: "Privacy Passports", href: "/dashboard/privacy-passports", icon: FileKey2 },
  { label: "Research Network", href: "/dashboard/research-network", icon: Network },
  { label: "Audit Trail", href: "/dashboard/audit", icon: FileText },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: 240,
        minHeight: "100vh",
        background: "#FFFFFF",
        borderRight: "1px solid #DCDCDC",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "24px 20px 20px",
          borderBottom: "1px solid #DCDCDC",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <Image
          src="/medilocker-logo.jpg"
          alt="MediLocker"
          width={32}
          height={32}
          style={{ borderRadius: "50%" }}
        />
        <span
          style={{
            fontFamily: "var(--font-sans)",
            fontWeight: 600,
            fontSize: 16,
            color: "#050505",
            letterSpacing: "-0.3px",
          }}
        >
          MediLocker
        </span>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "12px 8px", overflowY: "auto" }}>
        {NAV.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 12px",
                borderRadius: 6,
                marginBottom: 2,
                textDecoration: "none",
                fontSize: 13.5,
                fontWeight: active ? 500 : 400,
                color: active ? "#050505" : "#555555",
                background: active ? "#F2F2F2" : "transparent",
                transition: "background 0.1s, color 0.1s",
              }}
            >
              <Icon size={15} strokeWidth={active ? 2 : 1.5} />
              {item.label}
              {active && (
                <ChevronRight
                  size={12}
                  style={{ marginLeft: "auto", color: "#777777" }}
                />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        style={{
          padding: "16px 8px",
          borderTop: "1px solid #DCDCDC",
        }}
      >
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 12px",
            borderRadius: 6,
            textDecoration: "none",
            fontSize: 13.5,
            color: "#777777",
          }}
        >
          <LogOut size={15} strokeWidth={1.5} />
          Back to Site
        </Link>
        <div
          style={{
            padding: "8px 12px",
            fontSize: 11,
            color: "#AAAAAA",
            marginTop: 4,
          }}
        >
          MediLocker v2.0
          <br />
          CPU-only · Offline-first
        </div>
      </div>
    </aside>
  );
}

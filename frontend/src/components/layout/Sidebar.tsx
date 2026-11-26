"use client";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
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
import { api, type AuthUser } from "@/lib/api";

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
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    api
      .me()
      .then((res) => setUser(res.user))
      .catch(() => {});
  }, []);

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      // ignore
    }
    window.location.href = "/login";
  }

  async function handleOrgSwitch(orgId: string) {
    try {
      await api.switchOrg(orgId);
      window.location.reload();
    } catch {
      // ignore
    }
  }

  return (
    <aside
      style={{
        width: 244,
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
          padding: "20px 20px 16px",
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

      {/* Active Org Switcher */}
      {user && user.memberships.length > 0 && (
        <div style={{ padding: "12px 14px", borderBottom: "1px solid #EEEEEE" }}>
          <div style={{ fontSize: 10.5, color: "#777777", fontWeight: 600, marginBottom: 4, textTransform: "uppercase" }}>
            Organisation
          </div>
          <select
            value={user.active_org_id || ""}
            onChange={(e) => handleOrgSwitch(e.target.value)}
            style={{
              width: "100%",
              padding: "6px 8px",
              border: "1px solid #DCDCDC",
              borderRadius: 6,
              fontSize: 12.5,
              color: "#050505",
              background: "#FAFAFA",
            }}
          >
            {user.memberships.map((m) => (
              <option key={m.organisation_id} value={m.organisation_id}>
                {m.organisation_name} ({m.role})
              </option>
            ))}
          </select>
        </div>
      )}

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
      <div style={{ padding: "14px 8px", borderTop: "1px solid #DCDCDC" }}>
        {user && (
          <div style={{ padding: "4px 12px 10px", fontSize: 11.5, color: "#555555" }}>
            <div style={{ fontWeight: 600, color: "#050505" }}>{user.full_name}</div>
            <div style={{ color: "#777777", fontSize: 11 }}>{user.email}</div>
          </div>
        )}
        <button
          onClick={handleLogout}
          style={{
            width: "100%",
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "8px 12px",
            borderRadius: 6,
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 13.5,
            color: "#777777",
            textAlign: "left",
          }}
        >
          <LogOut size={15} strokeWidth={1.5} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}

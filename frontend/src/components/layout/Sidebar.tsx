"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Database,
  Building2,
  Shield,
  Brain,
  Swords,
  Network,
  HeartPulse,
  FileKey2,
  Share2,
  FileText,
  Settings,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";
import { api, type AuthUser } from "@/lib/api";

interface NavGroup {
  label: string;
  items: { label: string; href: string; icon: React.ElementType }[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "WORKSPACE",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Datasets", href: "/dashboard/datasets", icon: Database },
      { label: "Organisations", href: "/dashboard/organisations", icon: Building2 },
    ],
  },
  {
    label: "PRIVACY OPERATIONS",
    items: [
      { label: "Privacy Engine", href: "/dashboard/privacy-engine", icon: Shield },
      { label: "Privacy Intelligence", href: "/dashboard/privacy-intelligence", icon: Brain },
      { label: "Attack Simulator", href: "/dashboard/attack-simulator", icon: Swords },
    ],
  },
  {
    label: "CLINICAL & IDENTITY",
    items: [
      { label: "Identity Continuity", href: "/dashboard/identity-continuity", icon: Network },
      { label: "Clinical Integrity", href: "/dashboard/clinical-integrity", icon: HeartPulse },
    ],
  },
  {
    label: "TRUST & GOVERNANCE",
    items: [
      { label: "Privacy Passports", href: "/dashboard/privacy-passports", icon: FileKey2 },
      { label: "Research Network", href: "/dashboard/research-network", icon: Share2 },
      { label: "Audit Trail", href: "/dashboard/audit", icon: FileText },
    ],
  },
];

const CONFIG_GROUP: NavGroup = {
  label: "CONFIGURATION",
  items: [{ label: "Settings", href: "/dashboard/settings", icon: Settings }],
};

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function Sidebar({
  mobileOpen = false,
  onCloseMobile,
  collapsed = false,
  onToggleCollapse,
}: SidebarProps) {
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

  const renderNavGroup = (group: NavGroup) => (
    <div key={group.label} className="mb-4">
      {!collapsed && (
        <div className="px-3 mb-1.5 text-[10.5px] font-semibold tracking-[0.06em] uppercase text-[#666666]">
          {group.label}
        </div>
      )}
      <div className="space-y-0.5">
        {group.items.map((item) => {
          const active =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              title={collapsed ? item.label : undefined}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13.5px] transition-colors focus:outline-none focus:ring-2 focus:ring-[#050505] ${
                active
                  ? "bg-[#050505] text-white font-medium"
                  : "text-[#444444] hover:bg-[#F2F2F2] hover:text-[#050505]"
              } ${collapsed ? "justify-center px-2" : ""}`}
            >
              <Icon size={16} strokeWidth={active ? 2 : 1.6} className="shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </div>
    </div>
  );

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-[#E6E6E6]">
      {/* Brand header */}
      <div className="px-4 h-16 border-b border-[#E6E6E6] flex items-center justify-between shrink-0">
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 min-w-0 focus:outline-none"
        >
          <Image
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            width={30}
            height={30}
            className="rounded-full shrink-0"
          />
          {!collapsed && (
            <span className="font-semibold text-[16px] tracking-tight text-[#050505] truncate">
              MediLocker
            </span>
          )}
        </Link>

        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="hidden lg:inline-flex p-1.5 rounded-md text-[#666666] hover:text-[#050505] hover:bg-[#F2F2F2]"
          >
            {collapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </button>
        )}

        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Close navigation menu"
            className="lg:hidden p-1.5 rounded-md text-[#666666] hover:text-[#050505]"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Organisation selector directly below brand */}
      {!collapsed && user && user.memberships.length > 0 && (
        <div className="px-4 py-3 border-b border-[#E6E6E6] shrink-0">
          <label
            htmlFor="sidebar-org-select"
            className="block text-[10.5px] font-semibold tracking-[0.05em] uppercase text-[#666666] mb-1.5"
          >
            Organisation
          </label>
          <select
            id="sidebar-org-select"
            value={user.active_org_id || ""}
            onChange={(e) => handleOrgSwitch(e.target.value)}
            className="w-full px-2.5 py-1.5 text-[12.5px] font-medium text-[#050505] bg-[#F2F2F2] border border-[#E6E6E6] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#050505]"
          >
            {user.memberships.map((m) => (
              <option key={m.organisation_id} value={m.organisation_id}>
                {m.organisation_name} ({m.role})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Primary grouped navigation */}
      <nav
        aria-label="Sidebar Navigation"
        className="flex-1 overflow-y-auto px-3 py-4"
      >
        {NAV_GROUPS.map(renderNavGroup)}
      </nav>

      {/* Bottom configuration & account footer */}
      <div className="px-3 pt-3 pb-4 border-t border-[#E6E6E6] shrink-0">
        {renderNavGroup(CONFIG_GROUP)}

        {!collapsed && user && (
          <div className="px-3 py-2 mb-2 rounded-lg bg-[#F2F2F2] border border-[#E6E6E6]">
            <div className="text-[12px] font-semibold text-[#050505] truncate">
              {user.full_name}
            </div>
            <div className="text-[11px] text-[#666666] truncate">{user.email}</div>
          </div>
        )}

        <button
          type="button"
          onClick={handleLogout}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13.5px] text-[#666666] hover:bg-[#F2F2F2] hover:text-[#050505] transition-colors ${
            collapsed ? "justify-center px-2" : ""
          }`}
        >
          <LogOut size={16} strokeWidth={1.6} className="shrink-0" />
          {!collapsed && <span>Sign Out</span>}
        </button>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sticky sidebar */}
      <aside
        className={`hidden lg:block sticky top-0 h-screen shrink-0 transition-[width] duration-150 ${
          collapsed ? "w-[72px]" : "w-[256px]"
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile slide-over drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/40"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside className="relative w-[260px] max-w-[85vw] h-full z-10">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}

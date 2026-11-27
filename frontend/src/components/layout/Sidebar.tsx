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
  Building2,
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
  ChevronDown,
  ChevronRight,
  Sparkles,
  FileCheck2,
} from "lucide-react";
import { api, type AuthUser } from "@/lib/api";

const PRIMARY_NAV = [
  { num: "01", label: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { num: "02", label: "Protect Data", href: "/dashboard/protect-data", icon: Sparkles },
  { num: "03", label: "My Datasets", href: "/dashboard/datasets", icon: Database },
  { num: "04", label: "Reports", href: "/dashboard/reports", icon: FileCheck2 },
];

const ADVANCED_NAV = [
  { num: "05", label: "Privacy Intelligence", href: "/dashboard/privacy-intelligence", icon: Brain },
  { num: "06", label: "Attack Simulator", href: "/dashboard/attack-simulator", icon: Swords },
  { num: "07", label: "Identity Continuity", href: "/dashboard/identity-continuity", icon: Network },
  { num: "08", label: "Clinical Integrity", href: "/dashboard/clinical-integrity", icon: HeartPulse },
  { num: "09", label: "Privacy Passports", href: "/dashboard/privacy-passports", icon: FileKey2 },
  { num: "10", label: "Organisations", href: "/dashboard/organisations", icon: Building2 },
  { num: "11", label: "Research Network", href: "/dashboard/research-network", icon: Share2 },
  { num: "12", label: "Audit Trail", href: "/dashboard/audit", icon: FileText },
  { num: "13", label: "Settings", href: "/dashboard/settings", icon: Settings },
];

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
  const [offlineMode, setOfflineMode] = useState(false);
  const [judgeMode, setJudgeMode] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(() =>
    ADVANCED_NAV.some((item) => pathname.startsWith(item.href))
  );

  useEffect(() => {
    api.me().then((res) => setUser(res.user)).catch(() => {});
    api
      .authConfig()
      .then((c) => {
        setOfflineMode(Boolean(c.offline_mode));
        setJudgeMode(Boolean(c.judge_mode));
      })
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

  const sidebarContent = (
    <div className="flex flex-col h-full bg-white border-r border-[#DADADA]">
      {/* Brand Header */}
      <div className="px-5 h-16 border-b border-[#E5E5E5] flex items-center justify-between shrink-0">
        <Link href="/dashboard" className="flex items-center gap-2.5 min-w-0">
          <Image
            src="/medilocker-logo.jpg"
            alt="MediLocker"
            width={28}
            height={28}
            className="rounded-full shrink-0"
          />
          {!collapsed && (
            <span className="font-serif-display text-[19px] text-[#090909] truncate">
              MediLocker
            </span>
          )}
        </Link>

        {onToggleCollapse && (
          <button
            type="button"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="hidden lg:inline-flex p-1.5 rounded-md text-[#666666] hover:text-[#090909] hover:bg-[#F4F4F2]"
          >
            {collapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}
          </button>
        )}

        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Close navigation menu"
            className="lg:hidden p-1.5 rounded-md text-[#666666] hover:text-[#090909]"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Organisation Selector (Organisation Mode) or Local Workspace Label (Judge Mode) */}
      {!collapsed && judgeMode && (
        <div className="px-4 py-3 border-b border-[#E5E5E5] shrink-0">
          <div className="text-[10px] font-semibold tracking-[0.08em] uppercase text-[#888888] mb-1">
            Local Workspace
          </div>
          <div className="px-2.5 py-1.5 text-[12.5px] font-medium text-[#090909] bg-[#F4F4F2] border border-[#DADADA] rounded-lg">
            Local Evaluation Workspace
          </div>
        </div>
      )}
      {!collapsed && !judgeMode && user && user.memberships.length > 0 && (
        <div className="px-4 py-3 border-b border-[#E5E5E5] shrink-0">
          <label
            htmlFor="sidebar-org-select"
            className="block text-[10px] font-semibold tracking-[0.08em] uppercase text-[#888888] mb-1.5"
          >
            Active Organisation
          </label>
          <select
            id="sidebar-org-select"
            value={user.active_org_id || ""}
            onChange={(e) => handleOrgSwitch(e.target.value)}
            className="w-full px-2.5 py-1.5 text-[12.5px] font-medium text-[#090909] bg-[#F4F4F2] border border-[#DADADA] rounded-lg focus:outline-none focus:border-[#090909]"
          >
            {user.memberships.map((m) => (
              <option key={m.organisation_id} value={m.organisation_id}>
                {m.organisation_name} ({m.role})
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Primary & Expandable Advanced Navigation */}
      <nav aria-label="Sidebar Navigation" className="flex-1 overflow-y-auto px-3 py-4 space-y-3">
        <div className="space-y-0.5">
          {!collapsed && (
            <div className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-[#888888]">
              Workspace
            </div>
          )}
          {PRIMARY_NAV.map((item) => {
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
                title={collapsed ? `${item.num}. ${item.label}` : undefined}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-colors ${
                  active
                    ? "bg-[#E6E6E6] text-[#090909] font-semibold"
                    : "text-[#666666] hover:bg-[#F4F4F2] hover:text-[#090909]"
                } ${collapsed ? "justify-center px-2" : ""}`}
              >
                {!collapsed && (
                  <span className="text-[10.5px] font-mono text-[#888888] w-4 shrink-0">
                    {item.num}
                  </span>
                )}
                <Icon size={15} strokeWidth={active ? 2 : 1.6} className="shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </div>

        <div className="pt-2 border-t border-[#E5E5E5] space-y-0.5">
          {!collapsed && (
            <button
              type="button"
              onClick={() => setAdvancedOpen((o) => !o)}
              className="w-full px-3 py-1.5 flex items-center justify-between text-[10px] font-semibold uppercase tracking-[0.08em] text-[#888888] hover:text-[#090909]"
            >
              <span>Advanced Workspace</span>
              {advancedOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
            </button>
          )}
          {(collapsed || advancedOpen) &&
            ADVANCED_NAV.map((item) => {
              const active = pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onCloseMobile}
                  title={collapsed ? `${item.num}. ${item.label}` : undefined}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-colors ${
                    active
                      ? "bg-[#E6E6E6] text-[#090909] font-semibold"
                      : "text-[#666666] hover:bg-[#F4F4F2] hover:text-[#090909]"
                  } ${collapsed ? "justify-center px-2" : ""}`}
                >
                  {!collapsed && (
                    <span className="text-[10.5px] font-mono text-[#888888] w-4 shrink-0">
                      {item.num}
                    </span>
                  )}
                  <Icon size={15} strokeWidth={active ? 2 : 1.6} className="shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
        </div>
      </nav>

      {/* Bottom Identity, Offline Status & Sign Out */}
      <div className="px-3 py-3.5 border-t border-[#E5E5E5] shrink-0 space-y-2">
        {!collapsed && (
          <div className="px-3 py-2 rounded-lg bg-[#F4F4F2] border border-[#E5E5E5]">
            {judgeMode ? (
              <>
                <div className="text-[12px] font-semibold text-[#090909] truncate">
                  Local Evaluator
                </div>
                <div className="text-[11px] text-[#666666] truncate">
                  LOCAL EVALUATION MODE
                </div>
              </>
            ) : (
              user && (
                <>
                  <div className="text-[12px] font-semibold text-[#090909] truncate">
                    {user.full_name}
                  </div>
                  <div className="text-[11px] text-[#666666] truncate">
                    {user.active_role || user.platform_role}
                  </div>
                </>
              )
            )}
            <div className="text-[10.5px] text-[#888888] mt-1">
              {offlineMode ? "Offline Loopback · CPU-only" : "Local Engine · CPU-only"}
            </div>
          </div>
        )}

        {!judgeMode && (
          <button
            type="button"
            onClick={handleLogout}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] text-[#666666] hover:bg-[#F4F4F2] hover:text-[#090909] transition-colors ${
              collapsed ? "justify-center px-2" : ""
            }`}
          >
            <LogOut size={15} strokeWidth={1.6} className="shrink-0" />
            {!collapsed && <span>Sign out</span>}
          </button>
        )}
      </div>
    </div>
  );

  return (
    <>
      <aside
        className={`hidden lg:block sticky top-0 h-screen shrink-0 transition-[width] duration-150 ${
          collapsed ? "w-[72px]" : "w-[260px]"
        }`}
      >
        {sidebarContent}
      </aside>

      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/40"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside className="relative w-[264px] max-w-[85vw] h-full z-10">
            {sidebarContent}
          </aside>
        </div>
      )}
    </>
  );
}

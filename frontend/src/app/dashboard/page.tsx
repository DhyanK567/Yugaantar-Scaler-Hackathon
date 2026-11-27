"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, Lock } from "lucide-react";
import { api, ApiError, type AuthUser, type DashboardOverview } from "@/lib/api";
import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { ReleaseReadinessPanel } from "@/components/dashboard/ReleaseReadinessPanel";
import { GettingStartedPanel } from "@/components/dashboard/GettingStartedPanel";
import { MetricGrid } from "@/components/dashboard/MetricGrid";
import { ProcessingWorkflow } from "@/components/dashboard/ProcessingWorkflow";
import { RecentJobsPanel } from "@/components/dashboard/RecentJobsPanel";
import { AuditEventsPanel } from "@/components/dashboard/AuditEventsPanel";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [unauth, setUnauth] = useState(false);

  const loadDashboard = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError("");
    try {
      const [dash, me] = await Promise.all([api.dashboard(), api.me()]);
      setData(dash);
      setUser(me.user);
      setUnauth(false);
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 401) {
        setUnauth(true);
      } else {
        setError(e instanceof Error ? e.message : String(e));
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const id = setTimeout(() => {
      void loadDashboard(false);
    }, 0);
    return () => clearTimeout(id);
  }, [loadDashboard]);

  if (unauth) {
    return (
      <div className="py-16 max-w-md mx-auto text-center">
        <div className="bg-white border border-[#E6E6E6] rounded-2xl p-9 shadow-[0_1px_2px_rgba(0,0,0,0.03)]">
          <Lock size={28} className="text-[#050505] mx-auto mb-3.5" />
          <h1 className="text-[20px] font-bold text-[#050505] mb-2">
            Sign in required
          </h1>
          <p className="text-[13.5px] text-[#666666] mb-6">
            Authenticate to access organisation-scoped privacy telemetry.
          </p>
          <Link
            href="/login"
            className="inline-block px-6 py-2.5 rounded-xl bg-[#050505] text-white text-[13.5px] font-semibold hover:bg-[#222222]"
          >
            Go to Sign In
          </Link>
        </div>
      </div>
    );
  }

  const activeOrgName =
    user?.memberships.find((m) => m.organisation_id === user.active_org_id)
      ?.organisation_name ?? undefined;

  const hasProcessedData =
    (data?.metrics.files_processed.value ?? 0) > 0 ||
    (data?.recent_jobs.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* A. PAGE HEADER */}
      <DashboardHeader
        organisationName={activeOrgName}
        freshness={data?.freshness}
        refreshing={refreshing}
        onRefresh={() => loadDashboard(true)}
      />

      {error && (
        <div className="px-4 py-3 rounded-xl bg-[#FFFBF0] border border-[#E6D5A0] text-[13px] text-[#7A5C00] flex items-center gap-2.5">
          <AlertTriangle size={16} className="shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && !data ? (
        <div className="bg-white border border-[#E6E6E6] rounded-2xl p-12 text-center text-[13.5px] text-[#666666]">
          Loading MediLocker privacy telemetry…
        </div>
      ) : (
        data && (
          <>
            {/* B. OVERALL RELEASE READINESS */}
            <ReleaseReadinessPanel health={data.privacy_health} />

            {/* C. PRIMARY GET-STARTED / OPERATIONAL ACTION */}
            <GettingStartedPanel hasProcessedData={hasProcessedData} />

            {/* D. PRIVACY PERFORMANCE METRICS (3x2 grid) */}
            <MetricGrid metrics={data.metrics} />

            {/* E. PROCESSING WORKFLOW (6-stage visual pipeline) */}
            <ProcessingWorkflow latestJob={data.recent_jobs[0] ?? null} />

            {/* F. RECENT JOBS (7 cols) & G. AUDIT EVENTS (5 cols) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
              <div className="lg:col-span-7 min-w-0 flex flex-col">
                <RecentJobsPanel jobs={data.recent_jobs} />
              </div>
              <div className="lg:col-span-5 min-w-0 flex flex-col">
                <AuditEventsPanel events={data.audit_events} />
              </div>
            </div>
          </>
        )
      )}
    </div>
  );
}
